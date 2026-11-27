package com.example.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.File
import java.security.KeyStore
import java.util.concurrent.TimeUnit
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Owner-configured HTTPS service; credentials never appear in exports or logs. */
class BackendGateway(private val context: Context) {
    private val prefs = context.getSharedPreferences("mhvie_backend", Context.MODE_PRIVATE)
    private val client = OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS).readTimeout(90, TimeUnit.SECONDS).writeTimeout(90, TimeUnit.SECONDS).followRedirects(false).followSslRedirects(false).build()
    val endpoint: String
        get() = prefs.getString("endpoint", "").orEmpty()
    fun configured(): Boolean = endpoint.isNotBlank() && prefs.contains("token")
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val alias = "mhvie_backend_token_v1"
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    fun saveConnection(url: String, token: String) {
        val parsed = url.trim().toHttpUrlOrNull() ?: error("عنوان الخادم غير صالح")
        require(parsed.scheme == "https" && parsed.username.isEmpty() && parsed.password.isEmpty() && parsed.query == null && parsed.fragment == null) { "يلزم عنوان HTTPS دون كلمة مرور أو معاملات في الرابط" }
        val previous = endpoint.toHttpUrlOrNull()
        val originChanged = previous != null && (previous.scheme != parsed.scheme || previous.host != parsed.host || previous.port != parsed.port)
        require(!(originChanged && prefs.contains("token") && token.isBlank())) { "أعد إدخال رمز الوصول عند تغيير خادم الاتصال لحماية الرمز السابق" }
        val edit = prefs.edit().putString("endpoint", parsed.toString().trimEnd('/'))
        if (token.isNotBlank()) {
            require(token.length >= 32 && !token.contains('\n') && !token.contains('\r')) { "رمز الوصول يجب أن يكون 32 حرفًا على الأقل" }
            val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, key()) }
            edit.putString("token", Base64.encodeToString(cipher.iv + cipher.doFinal(token.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP))
        }
        check(edit.commit()) { "تعذر حفظ الاتصال" }
    }
    private fun token(): String {
        val encrypted = prefs.getString("token", null) ?: error("لم يُضبط رمز الوصول")
        val bytes = Base64.decode(encrypted, Base64.NO_WRAP)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(0, 12))) }
        return cipher.doFinal(bytes.copyOfRange(12, bytes.size)).toString(Charsets.UTF_8)
    }
    private fun request(route: String, method: String = "GET", body: okhttp3.RequestBody? = null, idempotencyKey: String? = null): okhttp3.Response {
        require(route.startsWith("v1/"))
        val base = (endpoint.trimEnd('/') + "/").toHttpUrlOrNull() ?: error("لم يُضبط عنوان الخادم")
        require(base.scheme == "https") { "HTTPS مطلوب" }
        val url = base.newBuilder().addPathSegments(route).build()
        val request = Request.Builder().url(url).header("Authorization", "Bearer ${token()}").apply {
            if (idempotencyKey != null) header("Idempotency-Key", idempotencyKey)
            method(method, body)
        }.build()
        return client.newCall(request).execute()
    }
    fun json(route: String, method: String = "GET", body: JSONObject? = null, idempotencyKey: String? = null): JSONObject {
        val requestBody = if (method == "GET") null else (body ?: JSONObject()).toString().toRequestBody("application/json".toMediaType())
        request(route, method, requestBody, idempotencyKey).use { response ->
            val data = response.body ?: error("استجابة خالية")
            val bytes = data.byteStream().use { readBounded(it, 4_000_000) }
            val parsed = runCatching { JSONObject(bytes.toString(Charsets.UTF_8)) }.getOrElse { error("استجابة غير صالحة HTTP ${response.code}") }
            check(response.isSuccessful) { "HTTP ${response.code}: ${parsed.optString("detail", "REQUEST_FAILED").take(200)}" }
            return parsed
        }
    }
    fun upload(file: File): String {
        require(file.isFile && file.length() in 1..10_000_000) { "رفع الصورة يتطلب حجمًا أقل من 10MB؛ الأصل محفوظ محليًا" }
        request("v1/inputs", "POST", file.asRequestBody("application/octet-stream".toMediaType())).use { response ->
            val body = response.body?.byteStream()?.use { readBounded(it, 16384) }?.toString(Charsets.UTF_8).orEmpty()
            check(response.isSuccessful) { "فشل رفع الصورة HTTP ${response.code}" }
            val input = JSONObject(body).getString("input")
            check(input.matches(Regex("[a-f0-9]{64}\\.(png|jpg|jpeg|webp)"))) { "INVALID_INPUT_ID" }
            return input
        }
    }
    fun download(route: String, output: File, limit: Int = 25_000_000, expectedSha256: String? = null): File {
        require(expectedSha256 != null && expectedSha256.matches(Regex("[a-f0-9]{64}"))) { "MISSING_ARTIFACT_FINGERPRINT" }
        output.parentFile?.mkdirs()
        val temp = File(output.parentFile, output.name + ".part")
        try {
            request(route).use { response ->
                check(response.isSuccessful) { "تحميل الملف HTTP ${response.code}" }
                val stream = response.body?.byteStream() ?: error("ملف خالٍ")
                stream.use { input -> temp.outputStream().use { out ->
                    val buffer = ByteArray(8192); var total = 0L
                    while (true) { val read = input.read(buffer); if (read == -1) break; total += read; check(total <= limit) { "FILE_SIZE_LIMIT" }; out.write(buffer, 0, read) }
                } }
            }
            val digest = java.security.MessageDigest.getInstance("SHA-256")
            temp.inputStream().use { input -> val buffer = ByteArray(8192); while (true) { val n = input.read(buffer); if (n == -1) break; digest.update(buffer, 0, n) } }
            check(digest.digest().joinToString("") { "%02x".format(it) } == expectedSha256) { "ARTIFACT_HASH_MISMATCH" }
            check(temp.renameTo(output)) { "تعذر حفظ الملف" }
            return output
        } catch (e: Exception) { temp.delete(); throw e }
    }
    private fun readBounded(input: java.io.InputStream, max: Int): ByteArray {
        val output = java.io.ByteArrayOutputStream(); val buffer = ByteArray(8192)
        while (true) { val n = input.read(buffer); if (n == -1) break; check(output.size() + n <= max) { "RESPONSE_SIZE_LIMIT" }; output.write(buffer, 0, n) }
        return output.toByteArray()
    }
}
