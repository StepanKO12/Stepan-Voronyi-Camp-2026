# Data Engineering Home Task Lecture 13

This folder contains intentionally imperfect raw CSV data.



## Files

* `customers.csv`
* `products.csv`
* `orders.csv`
* `order\\\_items.csv`



## Intentional data issues

The data includes:

* duplicate primary keys
* missing IDs
* invalid emails
* missing emails
* invalid timestamps
* negative and zero product prices
* unknown order statuses
* missing customer references
* missing product references
* missing order references
* invalid negative quantity
* mixed-case status values



## Candidate goal

Build a local ETL/ELT pipeline that reads these raw files, cleans them, loads them into a local database, and creates analytical output tables.

List of issues in the data where given. You should define what cleaning and what output tables should be created.

Recommended local stack:

* Python
* pandas
* PostgreSQL
* Docker Compose

Optional:

* SQLite
* dbt
* PySpark
* pytest



## Required output



* Detailed description what cleaning and why was done to the data.
* What output tables you created.
* Completely reusable code (I should be able to send the same 4 tables with different data and it should work)
* Make your code cross-platform, self-contained, reproducible. Imagine I have clean environment, using your code I should not spend more then 10 minutes to run it.



## Tips



* You can use AI tools for help, but the less you use it the better especially during cleaning process.
* You can't fail on cleaning process because there is no correct way to clean the data, your result will just reflect your thinking.

