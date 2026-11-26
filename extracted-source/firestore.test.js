const {
  initializeTestEnvironment,
  assertFails,
  assertSucceeds,
} = require("@firebase/rules-unit-testing");
const { test, before, after, beforeEach } = require("node:test");
const fs = require("node:fs");

let testEnv;
const PROJECT_ID = process.env.GCP_PROJECT || "demo-no-project";
const ALICE_UID = "alice_mhvie_01";
const BOB_UID = "bob_mhvie_02";

const [emulatorHost, emulatorPortStr] = (
  process.env.FIRESTORE_EMULATOR_HOST || "127.0.0.1:8085"
).split(":");
const emulatorPort = parseInt(emulatorPortStr, 10);

before(async () => {
  const rules = fs.readFileSync("./firestore.rules", "utf8");
  testEnv = await initializeTestEnvironment({
    projectId: PROJECT_ID,
    firestore: {
      rules,
      host: emulatorHost,
      port: emulatorPort,
    },
  });
});

after(async () => {
  if (testEnv) {
    await testEnv.cleanup();
  }
});

beforeEach(async () => {
  if (testEnv) {
    await testEnv.clearFirestore();
  }
});

test("Unauthenticated users cannot read or write batches, products, or brands", async () => {
  const unauthDb = testEnv.unauthenticatedContext().firestore();
  await assertFails(unauthDb.collection("users").doc(ALICE_UID).collection("batches").get());
  await assertFails(unauthDb.collection("users").doc(ALICE_UID).collection("products").get());
  await assertFails(
    unauthDb.collection("users").doc(ALICE_UID).collection("brands").doc("loreal").set({
      userId: ALICE_UID,
      brandName: "L'Oreal",
      processedCount: 1,
      successRate: 0.9,
      createdAt: new Date(Date.now() - 1000),
      updatedAt: new Date(Date.now() - 1000),
    })
  );
});

test("Owner can create, list, and partially update BatchJob & ProductRecord with Kotlin-aligned payloads", async () => {
  const aliceDb = testEnv.authenticatedContext(ALICE_UID).firestore();
  const ts = new Date(Date.now() - 5000);

  await assertSucceeds(
    aliceDb.collection("users").doc(ALICE_UID).collection("batches").doc("batch_001").set({
      userId: ALICE_UID,
      title: "دفعة العناية بالبشرة 001",
      status: "QUEUED",
      strategy: "STANDARD",
      targetImagesPerProduct: 5,
      totalProducts: 10,
      processedProducts: 0,
      foundProductsCount: 0,
      reviewProductsCount: 0,
      zeroResultCount: 0,
      discoveredImagesCount: 0,
      createdAt: ts,
      updatedAt: ts,
    })
  );

  await assertSucceeds(
    aliceDb.collection("users").doc(ALICE_UID).collection("batches").get()
  );

  await assertSucceeds(
    aliceDb.collection("users").doc(ALICE_UID).collection("batches").doc("batch_001").update({
      status: "RUNNING",
      processedProducts: 2,
      updatedAt: new Date(Date.now() - 1000),
    })
  );

  await assertSucceeds(
    aliceDb.collection("users").doc(ALICE_UID).collection("products").doc("prod_001").set({
      userId: ALICE_UID,
      batchId: "batch_001",
      brand: "CeraVe",
      productNameEn: "Foaming Facial Cleanser",
      productNameAr: "غسول رغوي للوجه",
      sizeWeight: "236ml",
      barcode: "3337875597197",
      identityConfidence: 0.94,
      status: "FOUND",
      zeroResultReason: "NONE",
      approvalStatus: "PENDING",
      discoveredCount: 4,
      matchedCount: 3,
      localOriginalPaths: ["file:///data/user/0/img1.jpg"],
      searchQueries: ["CeraVe Foaming Facial Cleanser 236ml"],
      createdAt: ts,
      updatedAt: ts,
    })
  );

  await assertSucceeds(
    aliceDb
      .collection("users")
      .doc(ALICE_UID)
      .collection("products")
      .doc("prod_001")
      .collection("candidates")
      .doc("cand_001")
      .set({
        userId: ALICE_UID,
        productId: "prod_001",
        imageUrl: "https://images.openbeautyfacts.org/example.jpg",
        pageUrl: "https://world.openbeautyfacts.org/product/3337875597197",
        sourceName: "Open Beauty Facts",
        sourceType: "OPEN_BEAUTY_DB",
        imageCategory: "A_OFFICIAL",
        rightsStatus: "COMMERCIAL_PERMITTED",
        matchScore: 0.92,
        brandMatchScore: 0.95,
        skuMatchScore: 0.91,
        aestheticScore: 0.85,
        widthPx: 1200,
        heightPx: 1200,
        reviewDecision: "PENDING",
        createdAt: ts,
        updatedAt: ts,
      })
  );
});

test("Security bounds: reject cross-user access, ghost fields, @DocumentId id field, and createdAt tampering", async () => {
  const aliceDb = testEnv.authenticatedContext(ALICE_UID).firestore();
  const bobDb = testEnv.authenticatedContext(BOB_UID).firestore();
  const ts = new Date(Date.now() - 5000);

  await assertSucceeds(
    aliceDb.collection("users").doc(ALICE_UID).collection("brands").doc("brand_cerave").set({
      userId: ALICE_UID,
      brandName: "CeraVe",
      officialWebsite: "https://www.cerave.com",
      processedCount: 3,
      successRate: 0.88,
      createdAt: ts,
      updatedAt: ts,
    })
  );

  // Cross-user read & write must fail
  await assertFails(bobDb.collection("users").doc(ALICE_UID).collection("brands").get());
  await assertFails(
    bobDb.collection("users").doc(ALICE_UID).collection("brands").doc("brand_cerave").update({
      brandName: "Hijacked",
      updatedAt: new Date(Date.now() - 500),
    })
  );

  // Ghost field & forbidden 'id' field must fail
  await assertFails(
    aliceDb.collection("users").doc(ALICE_UID).collection("brands").doc("brand_ghost").set({
      id: "brand_ghost",
      userId: ALICE_UID,
      brandName: "Test",
      processedCount: 0,
      successRate: 0.0,
      createdAt: ts,
      updatedAt: ts,
    })
  );

  // Tampering immutable createdAt must fail
  await assertFails(
    aliceDb.collection("users").doc(ALICE_UID).collection("brands").doc("brand_cerave").update({
      createdAt: new Date(Date.now() - 100),
      updatedAt: new Date(Date.now() - 100),
    })
  );

  // Future timestamp must fail
  await assertFails(
    aliceDb.collection("users").doc(ALICE_UID).collection("logs").doc("log_1").set({
      userId: ALICE_UID,
      level: "INFO",
      component: "Test",
      message: "Future timestamp",
      createdAt: new Date(Date.now() + 60000),
    })
  );
});
