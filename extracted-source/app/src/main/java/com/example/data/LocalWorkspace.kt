package com.example.data

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import com.example.model.*
import com.google.firebase.Timestamp
import com.squareup.moshi.FromJson
import com.squareup.moshi.Moshi
import com.squareup.moshi.ToJson
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.util.Date

/** Persistent local workspace inside the recovered app, independent of optional Firebase login. */
class LocalWorkspace(context: Context) : SQLiteOpenHelper(context, "mhvie_workspace.sqlite", null, 1) {
    private class TimestampAdapter {
        @ToJson fun encode(value: Timestamp): Long = value.toDate().time
        @FromJson fun decode(value: Long): Timestamp = Timestamp(Date(value))
    }
    val json: Moshi = Moshi.Builder().add(TimestampAdapter()).addLast(KotlinJsonAdapterFactory()).build()
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE records (kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind,id))")
    }
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit
    @Synchronized private fun <T> put(kind: String, id: String, value: T, type: Class<T>) {
        require(id.isNotBlank())
        val values = ContentValues().apply { put("kind", kind); put("id", id); put("payload", json.adapter(type).toJson(value)) }
        check(writableDatabase.insertWithOnConflict("records", null, values, SQLiteDatabase.CONFLICT_REPLACE) != -1L)
    }
    @Synchronized private fun <T> list(kind: String, type: Class<T>): List<T> = readableDatabase.query("records", arrayOf("payload"), "kind=?", arrayOf(kind), null, null, "rowid DESC").use { cursor ->
        buildList { while (cursor.moveToNext()) json.adapter(type).fromJson(cursor.getString(0))?.let { add(it) } }
    }
    fun products() = list("product", ProductRecord::class.java)
    fun batches() = list("batch", BatchJob::class.java)
    fun candidates() = list("candidate", DiscoveredImage::class.java)
    fun brands() = list("brand", BrandProfile::class.java)
    fun engines() = list("engine", EngineConfig::class.java)
    fun logs() = list("log", EngineAuditLog::class.java).take(250)
    fun links() = list("remote", RemoteLink::class.java)
    fun save(value: ProductRecord) = put("product", value.id, value, ProductRecord::class.java)
    fun save(value: BatchJob) = put("batch", value.id, value, BatchJob::class.java)
    fun save(value: DiscoveredImage) = put("candidate", value.id, value, DiscoveredImage::class.java)
    fun save(value: BrandProfile) = put("brand", value.id, value, BrandProfile::class.java)
    fun save(value: EngineConfig) = put("engine", value.id, value, EngineConfig::class.java)
    fun save(value: EngineAuditLog) = put("log", value.id, value, EngineAuditLog::class.java)
    fun save(value: RemoteLink) = put("remote", value.productId, value, RemoteLink::class.java)
    fun transaction(action: () -> Unit) { synchronized(this) { val db = writableDatabase; db.beginTransaction(); try { action(); db.setTransactionSuccessful() } finally { db.endTransaction() } } }
}

data class RemoteLink(
    val productId: String,
    val batchId: String,
    val inputId: String,
    val kind: String,
    val remoteBatchId: String,
    val jobId: String = "",
    val state: String = "QUEUED",
    val responseJson: String = "",
    val localArchive: String = "",
    val generation: Int = 0,
    val localOutputPath: String = ""
)
