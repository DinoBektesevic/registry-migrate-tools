"""
Separates statements in a file generated by .dump
sqlite3 method into file containing only table
create statements and only row insert statements.

Intended for use with a PostgreSQL RDS DB.
Last edited Dec. 2019.
Tested with w_2019_35, w_2019_38 build.
"""
import os
import shutil
import argparse
import subprocess
import tempfile

from sqlalchemy import create_engine

def parse_dump(dumpPath, tablesPath, rowsPath, s3RowsPath=None):
    """Separates a sqlite3 dump into table definitions and
    row insert statements. Will create both POSIXDatastore
    and S3Datastore compatible insert statements.

    Statements found in *posix files will likely only be
    compatible with SQLite DB.

    Statements in *s3 files are aimed at a PostgreSQL and
    S3Datastore. They contain updated statements to some
    INSERT statements pointing to POSIXDatastore, as well
    as converts the hex output SQLite makes to BYTEA
    acceptible string, as well as updates PostgreSQL
    counters in the last 2 lines of the file.

    Tables are harder to do automatically, best created
    with `Butler.makeRepo` call.

    Params
    ------
    dumpPath : `str`
        Path to file generated by sqlite3 .dump method.
    tablesPath : `str`
        Path to file in which table definition statements
        will be stored.
    rowsPath : `str`
        Path to file in which row insert statements will
        be stored.
    s3Rowspath : `str` or None
        Path to file in which row insert statements aimed
        at S3Datastore and PostgreSQL will be stored. By
        default rowsPath+'_s3'
    """
    # tables are what tables are, honestly best left to makeRepo
    with open(tablesPath, "w") as tablesFile:
        subprocess.call(["grep", "-v", "INSERT", dumpPath],
                        stdout=tablesFile)

    # dump the inserts into a temp file so that we can sort them
    # in case .dump had not done it right
    tmpRowsFile, tmpRowsPath = tempfile.mkstemp()
    subprocess.call(["grep", "INSERT", dumpPath],
                    stdout=tmpRowsFile)

    tableOrder = ("dataset_type", "dataset_type_dimensions", "execution", "run",
                  "instrument", "physical_filter", "detector", "visit", "exposure",
                  "skymap", "tract", "patch", "calibration_label", "visit_detector_region",
                  "visit_detector_skypix_join", "patch_skypix_join", "posix_datastore_records",
                  "dataset", "dataset_composition", "dataset_collection", "dataset_storage")

    for tblname in tableOrder:
        subprocess.call(f'grep "INTO {tblname} " {tmpRowsPath} >> {rowsPath}',
                        shell=True)

    # s3Rows then need not be sorted if we just copy
    # posix and substitute.
    if s3RowsPath is None:
        s3RowsPath = rowsPath + "_s3"

    shutil.copyfile(rowsPath, s3RowsPath)

    subprocess.call(["sed", "-i", "s/posix_datastore_records/s3datastorerecords/", s3RowsPath])
    subprocess.call(["sed", "-i", "s/POSIXDatastore/S3Datastore/", s3RowsPath])
    subprocess.call(["sed", "-i", "s=,X'=,'\\\\x=", s3RowsPath])

    # since this is intended for PostgreSQL we will update the
    # counters as if it's PostgreSQL. It's easier to remove the
    # lines later, than add them in when the file gets big.
    with open(s3RowsPath, "a") as s3Rows:
        s3Rows.writelines([
            "/* Update counters (not autoincremented since inserts contain the ids) */",
            "SELECT setval('dataset_id_seq', MAX(dataset_id)+1) FROM dataset;",
            "SELECT setval('execution_id_seq', MAX(execution_id)+1) FROM execution;"
            ])

description = """
Utilities for ingesting sqlite3 registry dump into an RDS database.

Files create* are created by parsing an sqlite .dump output.
Files create_tables_* contain SQL table CREATE statements.
Files create_rows_* contain SQL INSERT statements.

Two different create_rows_* files correspond to whether the
registry is being prepared to be used with a PosixDatastore
or an S3Datastore, as the two datastores require inserts
into different tables. The S3 variation assume the use of
PostgreSqlRegistry and issues an PostgreSQL appropriate
counter update statements in the last 2 lines of the file.
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("src", help="Path to dump file to use.")
    parser.add_argument("-t", "--tables", nargs="?",  default="create_tables_posix",
                        help=("Path to output file for table definitions.\n"
                              "Default: 'create_tables_posix'."))
    parser.add_argument("-r", "--rows", nargs="?", default="create_rows_posix",
                        help="Path to output file for row inserts.\n"
                        "Default: 'create_rows_posix'.")
    parser.add_argument("--s3-rows", nargs="?", default="create_rows_s3",
                        help="Path to output file for row inserts\n"
                        "assuming S3Datastore and PostgreSQL\n"
                        "Default: 'create_rows_s3'.")

    aargs = parser.parse_args()

    parse_dump(aargs.src, aargs.tables, aargs.rows, aargs.s3_rows)