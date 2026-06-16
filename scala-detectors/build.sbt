// SentinelTrace detection engine — pinned to the locked interop triple.
// JDK 17 (Temurin) + Scala 2.13.16 + Spark 4.0.0 + Delta 4.0.0. Spark 4 dropped
// Scala 2.12; serverless v4 demands exact 2.13.x; a cross-suffix mismatch is a
// runtime NoSuchMethodError, so these versions are not optional preferences.

ThisBuild / scalaVersion := "2.13.16"
ThisBuild / organization := "com.sentineltrace"
ThisBuild / version := "0.1.0-SNAPSHOT"

// Compile against Java 17 bytecode (serverless runs JDK 17; class file > 61 fails).
ThisBuild / javacOptions ++= Seq("--release", "17")
ThisBuild / scalacOptions ++= Seq("-deprecation", "-feature", "-unchecked", "-release", "17")

val sparkVersion = "4.0.0"
val deltaVersion = "4.0.0"

lazy val detectors = (project in file("."))
  .settings(
    name := "sentineltrace-detectors",
    libraryDependencies ++= Seq(
      "org.apache.spark" %% "spark-sql"  % sparkVersion % Provided,
      "org.apache.spark" %% "spark-core" % sparkVersion % Provided,
      "io.delta"         %% "delta-spark" % deltaVersion % Provided,
      // tests need Spark + Delta on the classpath (so not Provided in Test)
      "org.apache.spark" %% "spark-sql"  % sparkVersion % Test,
      "io.delta"         %% "delta-spark" % deltaVersion % Test,
      "org.scalatest"    %% "scalatest"  % "3.2.19" % Test,
      "org.scalacheck"   %% "scalacheck" % "1.18.1" % Test
    ),
    // Spark 4 on JDK 17 needs these module opens for the test JVM (Arrow/Unsafe).
    Test / fork := true,
    Test / javaOptions ++= Seq(
      "--add-opens=java.base/java.lang=ALL-UNNAMED",
      "--add-opens=java.base/java.nio=ALL-UNNAMED",
      "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
      "--add-opens=java.base/java.util=ALL-UNNAMED"
    )
  )
