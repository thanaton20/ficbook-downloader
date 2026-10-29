import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Release signing comes from a properties file kept outside the repository:
// storeFile, storePassword, keyAlias, keyPassword. Set FICBOOK_SIGNING to its path,
// or keep it at ~/.config/ficbook-downloader/android-signing.properties.
val signingFile = file(
    System.getenv("FICBOOK_SIGNING")
        ?: "${System.getProperty("user.home")}/.config/ficbook-downloader/android-signing.properties"
)
val signing = Properties().apply { if (signingFile.exists()) signingFile.inputStream().use { load(it) } }

android {
    namespace = "io.github.thanaton20.ficbook"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.thanaton20.ficbook"
        minSdk = 29
        targetSdk = 35
        versionCode = 3
        versionName = "0.5.1"
    }

    signingConfigs {
        if (signing.isNotEmpty()) {
            create("release") {
                storeFile = file(signing.getProperty("storeFile"))
                storePassword = signing.getProperty("storePassword")
                keyAlias = signing.getProperty("keyAlias")
                keyPassword = signing.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("release")
        }
    }

    sourceSets["main"].assets.srcDirs("../../shared")

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.webkit:webkit:1.12.1")
}
