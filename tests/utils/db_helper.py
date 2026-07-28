from contextlib import contextmanager

import pymysql
import pymysql.cursors


class DbHelper:
    def __init__(self, host, port, user, password, database):
        self.config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
        }

    @contextmanager
    def connection(self):
        conn = pymysql.connect(**self.config)
        try:
            yield conn
        finally:
            conn.close()

    def is_available(self) -> bool:
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
                    cur.fetchone()
            return True
        except pymysql.Error:
            return False

    def fetch_one(self, sql: str, params=None):
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchone()

    def fetch_all(self, sql: str, params=None):
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchall()

    def execute(self, sql: str, params=None):
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
            conn.commit()

    def count_sensor_data(self, device_id: str) -> int:
        row = self.fetch_one(
            'SELECT COUNT(*) AS cnt FROM sensor_data WHERE device_id = %s',
            (device_id,),
        )
        return int(row['cnt'])

    def count_device_status(self, device_id: str) -> int:
        row = self.fetch_one(
            'SELECT COUNT(*) AS cnt FROM device_status WHERE device_id = %s',
            (device_id,),
        )
        return int(row['cnt'])

    def get_device_status(self, device_id: str):
        return self.fetch_one(
            'SELECT * FROM device_status WHERE device_id = %s',
            (device_id,),
        )

    def get_latest_sensor_row(self, device_id: str):
        return self.fetch_one(
            '''
            SELECT * FROM sensor_data
            WHERE device_id = %s
            ORDER BY recorded_at DESC
            LIMIT 1
            ''',
            (device_id,),
        )

    def count_alarm_records(self, device_id: str) -> int:
        row = self.fetch_one(
            'SELECT COUNT(*) AS cnt FROM alarm_records WHERE device_id = %s',
            (device_id,),
        )
        return int(row['cnt'])

    def count_pending_commands(self, device_id: str) -> int:
        row = self.fetch_one(
            'SELECT COUNT(*) AS cnt FROM pending_commands WHERE device_id = %s',
            (device_id,),
        )
        return int(row['cnt'])

    def count_remote_operations(self, device_id: str) -> int:
        row = self.fetch_one(
            'SELECT COUNT(*) AS cnt FROM remote_operation_records WHERE device_id = %s',
            (device_id,),
        )
        return int(row['cnt'])

    def get_latest_operation(self, device_id: str):
        return self.fetch_one(
            '''
            SELECT * FROM remote_operation_records
            WHERE device_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            ''',
            (device_id,),
        )

    def get_latest_alarm(self, device_id: str, alarm_type: str | None = None):
        sql = '''
            SELECT * FROM alarm_records
            WHERE device_id = %s
        '''
        params: list = [device_id]
        if alarm_type:
            sql += ' AND alarm_type = %s'
            params.append(alarm_type)
        sql += ' ORDER BY created_at DESC LIMIT 1'
        return self.fetch_one(sql, tuple(params))

    def cleanup_device(self, device_id: str):
        tables = [
            'pending_commands',
            'voice_command_records',
            'remote_operation_records',
            'alarm_records',
            'sensor_data',
            'device_status',
        ]
        with self.connection() as conn:
            with conn.cursor() as cur:
                for table in tables:
                    cur.execute(f'DELETE FROM {table} WHERE device_id = %s', (device_id,))
            conn.commit()
