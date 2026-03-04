import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    id("com.google.devtools.ksp")
}

val localProperties = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) {
        file.inputStream().use { input -> load(input) }
    }
}

val groceryLocalProperties = Properties().apply {
    val file = rootProject.file("grocery.local.properties")
    if (file.exists()) {
        file.inputStream().use { input -> load(input) }
    }
}

android {
    namespace = "com.example.grocerystoreorganizer"
    compileSdk {
        version = release(36)
    }

    defaultConfig {
        applicationId = "com.example.grocerystoreorganizer"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        val grpcHost = providers.gradleProperty("grpcHost")
            .orElse(
                providers.provider {
                    groceryLocalProperties.getProperty("grpcHost")
                        ?: localProperties.getProperty("grocery.grpcHost")
                        ?: "10.0.2.2"
                }
            )
            .get()
        val grpcPort = providers.gradleProperty("grpcPort")
            .orElse(
                providers.provider {
                    groceryLocalProperties.getProperty("grpcPort")
                        ?: localProperties.getProperty("grocery.grpcPort")
                        ?: "50051"
                }
            )
            .get()
        buildConfigField("String", "GRPC_HOST", "\"$grpcHost\"")
        buildConfigField("int", "GRPC_PORT", grpcPort)
        buildConfigField("boolean", "USE_REMOTE_DB", "true")

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }

}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.extended)
    implementation(libs.play.services.location)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    implementation(libs.kotlinx.coroutines.play.services)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)
    implementation(libs.grpc.okhttp)
    implementation(libs.grpc.protobuf.lite)
    implementation(libs.grpc.stub)
    implementation(libs.protobuf.javalite)
}
