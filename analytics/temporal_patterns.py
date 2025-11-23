import datetime 
from collections import Counter, defaultdict

from .base_module import AnalyticsModule
from aqt import mw

class TemporalLearningPatterns(AnalyticsModule):
    #Computes temporal patterns in user learning behavior
    def convert_timestamp(self, ms_timestamp):
        return datetime.datetime.fromtimestamp(ms_timestamp/1000)
    
    def compute_hour_distribution(self, revlog):
        #Counts how many reviews occur in each hour of the day
        hours = [self.convert_timestamp(r[0]).hour for r in revlog]
        return Counter(hours)
    
    def compute_weekday_distribution(self,revlog):
        #Counts how many reviews occur on each day of the week
        weekdays = [self.convert_timestamp(r[0]).weekday() for r in revlog]
        return Counter(weekdays)
    
    def compute_session_lengths(self, revlog, threshold_minutes=15):
        #Estimate study session lengths by grouping reviews close in time
        if not revlog:
            return []
        timestamps = sorted([r[0] for r in revlog])
        session_lengths = []

        session_start = timestamps[0]
        previous = timestamps[0]

        for t in timestamps[1:]:
            gap_minutes = (t-previous)/1000/60
            if gap_minutes > threshold_minutes:
                #End previous session
                session_lengths.append(
                    (previous - session_start)/1000/60
                )
                session_start = t
            previous = t
        
        #Final session
        session_lengths.append((previous-session_start)/1000/60)
        
        return session_lengths

    def fetch_revlog(self, deck_id=None):
        """Return revlog rows with the timestamp as the first column.
        If `deck_id` is provided, only return revlog rows for cards in that deck.
        Each row is returned in the form (time, cid, id, ease, ivl, lastIvl, type)
        where `time` is the millisecond timestamp stored in revlog.
        """
        # Some Anki versions/storage may have `revlog.time` in seconds (10-digit)
        # or milliseconds (13-digit). To be robust, fetch the raw `time` value
        # and convert to milliseconds in Python based on magnitude.
        if deck_id is None:
            query = """
                SELECT time, cid, id, ease, ivl, lastIvl, type
                FROM revlog
            """
            rows = mw.col.db.all(query)
        else:
            query = """
                SELECT revlog.time AS time, revlog.cid, revlog.id, revlog.ease, revlog.ivl, revlog.lastIvl, revlog.type
                FROM revlog
                JOIN cards ON revlog.cid = cards.id
                WHERE cards.did = :did
            """
            rows = mw.col.db.all(query, did=deck_id)

        if not rows:
            return rows

        # Determine whether `time` appears to be seconds or milliseconds by
        # inspecting the largest value. Current epoch in seconds is ~1e9,
        # in milliseconds ~1e12. Use threshold to distinguish.
        try:
            max_raw = max(r[0] for r in rows if r[0] is not None)
        except Exception:
            max_raw = 0

        # If max_raw looks like milliseconds already (>= 1e11), keep as-is.
        # Otherwise assume seconds and multiply by 1000.
        needs_mul = False
        if max_raw and max_raw < 1e11:
            needs_mul = True

        if needs_mul:
            converted = [((r[0] * 1000) if r[0] is not None else None,) + tuple(r[1:]) for r in rows]
        else:
            converted = [(r[0],) + tuple(r[1:]) for r in rows]

        # Debug: print detection info to help user diagnose unit issues.
        try:
            print(f"[temporal_patterns] fetch_revlog deck_id={deck_id} rows={len(rows)} max_raw={max_raw} needs_mul={needs_mul}")
        except Exception:
            pass

        return converted
    
    def compute(self):
        #Returns dictionary of insights ready for display

        revlog = self.fetch_revlog()
        if not revlog:
            return {"Error": "No review history was found."}
        
        hour_dist = self.compute_hour_distribution(revlog)
        weekday_dist = self.compute_weekday_distribution(revlog)
        sessions = self.compute_session_lengths(revlog)

        #Most active hour hour(0-23)
        most_active_hour = hour_dist.most_common(1)[0][0]

        #Most active weekday (0-6, where 0 is Monday)
        weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        most_active_day_index = weekday_dist.most_common(1)[0][0]
        most_active_weekday = weekday_names[most_active_day_index]

        average_session_length = (
            sum(sessions) / len(sessions)
            if sessions else 0
        )

        return {
            "Most Active Hour": f"{most_active_hour}:00",
            "Most Active Weekday": most_active_weekday,
            "Total Reviews": len(revlog),
            "Hourly Distribution": dict(hour_dist),
            "Weekday Distribution": dict(weekday_dist),
            "Average Session Length (min)": round(average_session_length, 2),
            "Session Count": len(sessions),
        }

