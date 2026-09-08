import pymssql


class Database:
    def __init__(self, config):
        self.schema = config["schema"]
        self.config = config
        self.conn = None

    def connect(self):
        if self.conn is None:
            try:
                self.conn = pymssql.connect(
                    server=self.config["host"],
                    user=self.config["user"],
                    password=self.config["password"],
                    database=self.config["database"],
                    port=self.config["port"]
                )
                print(f"Connected")
                return True
            except Exception as e:
                print(f"Connection failed: {e}")
                return False
        return True

    def query(self, sql, params=None):
        try:
            self.connect()
            if self.conn:
                cursor = self.conn.cursor(as_dict=True)
                if params:
                    cursor.execute(sql, params)
                else:
                    sql = sql.replace("%%", "%")
                    cursor.execute(sql)
                rows = cursor.fetchall()
                return 1, rows, None
            return 0, None, "DB connect fail"
        except Exception as e:
            return 0, None, str(e)

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            print("Connection closed")