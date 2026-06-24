# get urls
TRIP_UPDATES_URL = "https://go.bkk.hu/api/query/v1/ws/gtfs-rt/full/TripUpdates.pb"
GTFS_ZIP_URL = "https://go.bkk.hu/api/static/v1/public-gtfs/budapest_gtfs.zip"

# define delay category thresholds (TODO clarify! open to redifne)
# values are in seconds
ON_TIME_MAX = 120  # within 2 minutes = on_time
MINOR_MAX = 300  # between 2 and 5 = minor_delay
# more than 5 = major_delay
