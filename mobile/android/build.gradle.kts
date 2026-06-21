allprojects {
    repositories {
        google()
        mavenCentral()
        maven { url = uri("https://cache-redirector.jetbrains.com/repo1.maven.org/maven2") }
    }

    // Override after plugin evaluation: align Java/Kotlin to 17 and compileSdk to 36.
    // Required because AGP 7.x plugins default Java to 11 and compileSdk to 34.
    afterEvaluate {
        (extensions.findByName("android") as? com.android.build.gradle.BaseExtension)?.apply {
            compileSdkVersion(36)
            compileOptions {
                sourceCompatibility = JavaVersion.VERSION_17
                targetCompatibility = JavaVersion.VERSION_17
            }
        }
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinJvmCompile>().configureEach {
            compilerOptions.jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
        }
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
