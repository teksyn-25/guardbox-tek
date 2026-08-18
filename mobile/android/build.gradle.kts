allprojects {
    repositories {
        google()
        mavenCentral()
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

// file_picker pins compileSdk 34, but a transitive dependency
// (flutter_plugin_android_lifecycle) now requires compileSdk 36+. Match the app
// module's compileSdk (36, per the installed SDK) so the AAR metadata check passes.
project(":file_picker") {
    afterEvaluate {
        extensions.configure<com.android.build.gradle.LibraryExtension> {
            compileSdk = 36
        }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
