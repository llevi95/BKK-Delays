"""Run once: python tests/fixtures/make_fixture.py -> sample_trip_updates.pb"""
from pathlib import Path
from google.transit import gtfs_realtime_pb2

feed = gtfs_realtime_pb2.FeedMessage()
feed.header.gtfs_realtime_version = "2.0"

ent = feed.entity.add()
ent.id = "1"
tu = ent.trip_update
tu.trip.trip_id = "TRIP_1"
tu.trip.route_id = "ROUTE_1"
tu.trip.start_date = "20260623"

stu = tu.stop_time_update.add()
stu.stop_id = "STOP_1"
stu.stop_sequence = 1
stu.arrival.time = 1782216827      # absolute predicted epoch, like the real feed
stu.departure.time = 1782216873

out = Path(__file__).parent / "sample_trip_updates.pb"
out.write_bytes(feed.SerializeToString())
print("wrote", out)
