# Databricks notebook source
# MAGIC %sql 
# MAGIC
# MAGIC CREATE CATALOG IF NOT EXISTS fmcg;
# MAGIC USE catalog fmcg;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE SCHEMA IF NOT EXISTS fmcg.gold;
# MAGIC CREATE SCHEMA IF NOT EXISTS fmcg.bronze;
# MAGIC CREATE SCHEMA IF NOT EXISTS fmcg.silver;