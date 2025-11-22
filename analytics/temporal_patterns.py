import datetime 
from collections import Counter, defaultdict

from .base_module import AnalyticsModule

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

