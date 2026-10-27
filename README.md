# Atlikon FMCG Data Pipeline

A Databricks pipeline that merges an acquired company's order data into a parent company's analytics tables. The child company sends daily CSV files to S3. The parent company reports at monthly grain, so the pipeline cleans the child data, rolls it up to months and merges it into the parent gold tables.

## Architecture

```
S3 landing (daily CSVs)
   -> Bronze (raw Delta tables, file name and size kept)
   -> Silver (cleaned, deduplicated, product_code attached)
   -> Child gold (sb_fact_orders, sb_dim_*)
   -> MERGE into parent gold (fact_orders, dim_customers, dim_products, dim_gross_price)
   -> SQL view (vw_fact_orders_enriched)
   -> Dashboard
```

Processed files are moved from `landing/` to `processed/` in S3 after each load.

## Tech stack

Databricks, PySpark, Spark SQL, Delta Lake, Unity Catalog, AWS S3, Databricks SQL dashboards

## Data volumes

| Item | Count |
|---|---|
| Child order lines (raw) | 61,777 (51,810 full load + 9,967 incremental) |
| Daily CSV files | 182 (151 full load + 31 incremental) |
| Child monthly rows merged into parent | 3,672 (3,060 full load + 612 incremental) |
| Parent fact table (before child merge) | 93,055 rows, 23 months, 397 products, 18 customers |

## Data cleaning (silver layer)

**Orders**
- Dropped 3,087 rows with null `order_qty` (about 5%)
- Removed 2,773 duplicate rows on order_id, date, customer_id, product_id and quantity
- Standardized 4 date formats, including text dates with a weekday prefix (about 80% of rows)
- Mapped 6,242 non-numeric customer IDs to a fallback key `999999` so the rows are kept

**Customers**
- Removed duplicate customer_id records (39 rows, 35 unique IDs)
- Corrected 7 misspelled city variants to 3 cities
- Filled 4 null cities from business-confirmed values
- Trimmed whitespace and fixed title casing

**Products**
- Removed duplicate product_id records
- Corrected the "Protien" spelling in names and categories
- Added a `division` column and parsed `variant` from the product name
- Generated a deterministic `product_code` (SHA-256 of the product name)

**Prices**
- Parsed 4 date formats into one month date
- Converted 11 negative values to positive and set 6 non-numeric values to 0
- Kept one price per product and year, preferring the latest non-zero value

## Incremental load

Each new batch is appended to bronze and loaded into a temporary staging table. Silver and child gold are updated with Delta `MERGE`. Only the months present in the batch are recalculated and merged into the parent fact table. For December 2025 that was 1 month and 612 rows, instead of a full rebuild. Staging tables are dropped after the run.

## Repository structure

```
0_data/          sample parent and child source files (full and incremental)
1_codes/
  1_setup/                    catalog and schema creation, date dimension, shared utilities
  2_dimension_data_processing/ customers, products, pricing
  3_fact_data_processing/     full load and incremental load
2_dashboarding/  enriched SQL view and dashboard export (PDF)
resources/       architecture diagram
```

## How to run

1. Create the catalog and schemas with `setup_catalog`, then build `dim_date`.
2. Load the parent files into `fmcg.gold` (`dim_customers`, `dim_products`, `dim_gross_price`, `fact_orders`).
3. Upload the child files to S3 and update the `s3://` paths and the `%run` utilities path in the notebooks to match your workspace.
4. Run the dimension notebooks in this order: customers, products, pricing. Pricing joins to the silver products table.
5. Run `1_full_load_fact`, then `2_incremental_load_fact` for each later batch.
6. Run `denormalise_table_query_fmcg.txt` to create the enriched view for the dashboard.

## Dashboard

The dashboard shows total revenue (₹105.34B), units sold (34.13M), and revenue by customer, channel, category and variant. The export in `2_dashboarding/` was taken on 24 Nov 2025, before the December incremental load.

## Known issues

- Product `25891502` is stored as `XYZ123` in the child products file. The cleaning step replaces it with `999999`, so its 2,990 valid order lines are dropped by the inner join with products. The other 3 invalid product IDs (2,895 lines) are dropped on purpose.
- The `999999` fallback customer key groups all invalid customers into one record.
- Customer and product master data are overwritten on each run, so history is not versioned.

## Data source
https://drive.google.com/drive/folders/1i8ew8Rm9JUMsFaKqQ8BEIUQzWYxcZXNt?usp=sharing
