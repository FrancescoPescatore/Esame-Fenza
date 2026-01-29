"""
YoutubeSparkConsumer - Spark Structured Streaming Consumer for YouTube Comments

This script consumes YouTube comments from Kafka (published by YoutubeProducer.py),
applies transformations using Spark Structured Streaming, and writes results to MongoDB.

Architecture:
- Input: Kafka topic 'youtube-comments'
- Processing: Spark Structured Streaming with filtering
- Output: MongoDB collection 'CommentiLive'
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, length, current_timestamp, udf
from pyspark.sql.types import StructType, StringType
import os

# -----------------------------
# CONFIGURAZIONE
# -----------------------------
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = "youtube-comments"
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DATABASE = "cinematch_db"
MONGODB_COLLECTION = "CommentiLive"
MIN_COMMENT_LENGTH = 80

# Spark MongoDB connector URI
MONGO_OUTPUT_URI = f"{MONGODB_URL}/{MONGODB_DATABASE}.{MONGODB_COLLECTION}"

# -----------------------------
# SPARK SESSION
# -----------------------------
spark = SparkSession.builder \
    .appName("YouTubeCommentsStreaming") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/youtube_checkpoint") \
    .config("spark.mongodb.output.uri", MONGO_OUTPUT_URI) \
    .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.2") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# -----------------------------
# SCHEMA
# -----------------------------
schema = StructType() \
    .add("comment_id", StringType()) \
    .add("author", StringType()) \
    .add("text", StringType()) \
    .add("published_at", StringType())

# -----------------------------
# STREAM DA KAFKA
# -----------------------------
raw_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "latest") \
    .load()

# Parsing del JSON
comments = raw_stream.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# -----------------------------
# PROCESSING (Spark Structured Streaming)
# -----------------------------
# Filter by minimum text length
processed = comments \
    .filter(length(col("text")) > MIN_COMMENT_LENGTH) \
    .withColumn("processed_at", current_timestamp()) \
    .selectExpr(
        "comment_id as _id",
        "author as utente_commento",
        "published_at as data_ora",
        "cast(null as double) as valore_sentiment",
        "text as commento"
    )


# -----------------------------
# SCRIVI SU MONGODB
# -----------------------------
def write_to_mongodb(batch_df, batch_id):
    """
    Writes each micro-batch to MongoDB.
    Uses foreachBatch for MongoDB sink with upsert semantics.
    """
    if batch_df.count() > 0:
        print(f"[Spark] Batch {batch_id}: Writing {batch_df.count()} comments to MongoDB")
        
        batch_df.write \
            .format("mongo") \
            .mode("append") \
            .option("replaceDocument", "false") \
            .save()


# Start streaming query with MongoDB sink
query = processed.writeStream \
    .foreachBatch(write_to_mongodb) \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/youtube_checkpoint") \
    .start()

print(f"[Spark] Streaming started - Kafka: {KAFKA_BROKER} -> MongoDB: {MONGODB_COLLECTION}")
print("[Spark] Waiting for termination... (Ctrl+C to stop)")

query.awaitTermination()
