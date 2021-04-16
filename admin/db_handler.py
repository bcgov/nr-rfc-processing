import os
import sqlite3
import logging

import pandas as pd

import admin.constants as const

class DBHandler(object):
    """
    Database Handler Class
    """
    def __init__(self):
        """
        Setup db connection and missing tables
        """
        super().__init__()
        self.conn = self._init_connection()
        self.logger = logging.getLogger(__name__)
        self._setup_tables()

    def __del__(self):
        """
        Clean db connection on exit
        """
        self.conn.close()

    def _init_connection(self):
        """Initialize connection to db

        Returns
        -------
        sqlite3 connection
            Connector object to a sqlite3 db
        """
        return sqlite3.connect(os.path.join(const.ANALYSIS, 'analysis.db'))

    def _setup_tables(self):
        """
        Internal function to set up missing tables
        """
        self.logger.info('Creating tables if not exists')
        for sat in ['modis', 'viirs', 'sentinel2']:
            create = f"CREATE TABLE IF NOT EXISTS {sat} ( \
                                            id integer PRIMARY KEY, \
                                            name text NOT NULL, \
                                            date_ date, \
                                            snow_coverage real, \
                                            nodata real, \
                                            below_threshold real \
                                        );"
            self.execute(create)


    def get_conn(self):
        """
        Allow the connection object to be used

        Returns
        -------
        sqlite3 connector
            Connection object to sqlite3 db
        """
        return self.conn
    
    def execute(self, stmt):
        """Execute and commit a generic statement to the db

        Parameters
        ----------
        stmt : str
            sqlite3 statement
        """
        try:
            cur = self.conn.cursor()
            cur.execute(stmt)
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.error(e)

    def insert(self, sat, name, date_, coverage, nodata, below_threshold):
        """Insert statement 

        Parameters
        ----------
        sat : str
            Satellite table to reference [modis | viirs | sentinel2]
        name : str
            Name of entry to be inserted (watershed/basin name)
        date_ : str
            Date in format YYYY.MM.DD
        coverage : float
            snow % coverage
        nodata : float
            % of nodata in aoi
        below_threshold : float
            % of values below 20% NDSI threshold
        """        
        insert = f"""INSERT OR REPLACE INTO {sat}(
                id, name, date_, snow_coverage, nodata, below_threshold
            ) VALUES(
                (SELECT id FROM {sat} WHERE name='{name}' AND date_='{date_}'),'{name}', '{date_}', {coverage}, {nodata}, {below_threshold}
            );
            """
        try:
            cur = self.conn.cursor()
            cur.execute(insert)
            self.conn.commit()
        except sqlite3.Error as e:
            self.logger.error(e)

    def select(self, stmt):
        """Select statement for sqlite3 db

        Parameters
        ----------
        stmt : str
            sqlite3 statement to be executed

        Returns
        -------
        tuple
            Tuple of snow statistics for a given aoi
        """
        cur = self.conn.cursor()
        cur.execute(stmt)
        return cur.fetchone()


    def db_to_csv(self):
        try:
            df_modis = pd.read_sql(f"SELECT * FROM modis", self.conn)
            df_modis['satellite'] = 'modis'
        except:
            df_modis = pd.DataFrame()
        try:
            df_viirs = pd.read_sql(f"SELECT * FROM viirs", self.conn)
            df_viirs['satellite'] = 'viirs'
        except:
            df_viirs = pd.DataFrame()
        try:
            df_s2 = pd.read_sql(f"SELECT * FROM sentinel2", self.conn)
            df_s2['satellite'] = 'sentinel2'
        except:
            df_s2 = pd.DataFrame()
        df = pd.concat([df_modis, df_viirs, df_s2])
        df.to_csv(os.path.join(const.ANALYSIS,'analysis.csv'), index=False)