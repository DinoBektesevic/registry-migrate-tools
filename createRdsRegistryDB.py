"""
Migrates, more precisely recreates, gen3.sqlite3 database that
accompanies ci_hsc_gen3 by connecting to the given database and
then executing pre-prepared statements in targeted files.

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
from sqlalchemy import exc


def clean(constr):
    """
    """
    targetEngine = create_engine(constr)

    drop_order = ("dataset_collection", "dataset_composition", "dataset_consumers",
                  "dataset_storage", "dataset_type_dimensions", "dataset_type_metadata",
                  "s3datastorerecords", "dataset", "dataset_type", "detector", "execution",
                  "exposure", "instrument", "patch", "patch_skypix_join", "physical_filter",
                  "quantum", "run", "skymap", "tract", "visit", "visit_detector_region",
                  "visit_detector_skypix_join", "calibration_label")

    for tblname in drop_order:
        try:
            targetEngine.execute(f"DROP TABLE {tblname} CASCADE;")
        except exc.SQLAlchemyError:
            # not the best, but if ingest was bad, tables could and
            # don't have to exist
            pass


def ingest_dump(constr, rowsFile, tablesFile=None, createTables=False, createRows=True):
    """Connects to target DB and executes SQL statements found in
    tables and rows file.

    Parameters
    ----------
    constr : `str`
        Connection string for the target DB.
    rowsFile : `str`
        Path to file containing INSERT statements.
    tablesFile : `str` or `None`
        Path to file containing CREATE statements.
    createTables : `bool`
        When True statements found in tablesFile
        will be executed.
    createRows : `bool`
        When True statements found in rowsFile
        will be executed.
    """
    targetEngine = create_engine(constr)

    # don't try outside block, error msg will echo all
    # the lines in the files.
    if createTables:
        print("Creating tables ...")
        createTablesSql = open(tablesFile).read()
        try:
            a = targetEngine.execute(createTablesSql)
        except Exception as e:
            print(e.args)
            print(type(e))

    if createRows:
        print("Ingesting rows ...")
        dataDumpSql = open(rowsFile).read()
        try:
            a = targetEngine.execute(dataDumpSql)
        except Exception as e:
            print(e.args)
            print(type(e))
            #print(e.orig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Utilities for ingesting sqlite3 registry dump into an RDS database.")
    parser.add_argument("constr", help="Connection string, or path to file containing one.")
    parser.add_argument("--create-tables", help="Issue table CREATE statements.",
                        action='store_const', const=True, default=False, dest="createTables")
    parser.add_argument("--skip-rows", help="Skip inserting rows.",
                        action='store_const', const=True, default=False, dest="skipRows")
    parser.add_argument("--clean", help="Drop all tables.",
                        action='store_const', const=True, default=False, dest="clean")
    parser.add_argument("-t", "--tables", nargs="?",  default="create_tables_s3",
                        help=("Path to file with table definitions. It is assumed statements "
                              "have been processed appropriately and are correct "
                              "with respect to targeted database. Default: create_tables_s3"))
    parser.add_argument("-r", "--rows", nargs="?", default="create_rows_s3",
                        help=("Path to file with row inserts. It is assumed statements "
                              "have been processed appropriately and are correct "
                              "with respect to DB, datastore and registry "
                              "intended to be used. Default: 'create_rows_s3'."))
    aargs = parser.parse_args()

    if os.path.exists(aargs.constr) and os.path.isfile(aargs.constr):
        conStr = open(aargs.constr).read().strip()
    else:
        conStr = aargs.consstr

    if aargs.clean:
        clean(conStr)
    else:
        ingest_dump(conStr, aargs.rows, aargs.tables,
                    createTables=aargs.createTables,
                    createRows=not aargs.skipRows)
