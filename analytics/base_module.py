from aqt import mw

class AnalyticsModule:
    #Base class with shared helper methods for all analytics modules

    def fetch_revlog(self):
        #Retrieve all revlog rows from the Anki database
        query = """
            SELECT id, cid, ease, ivl, lastIvl, time, type
            FROM revlog
        """
        return mw.col.db.all(query)