#!/usr/bin/env python
# coding=utf-8

import transitfeed
import sys
import argparse
from core.configuration import Configuration
from core.osm_connector import OsmConnector
from core.creator_factory import CreatorFactory

# Handle arguments
parser = argparse.ArgumentParser(
    prog='osm2gtfs', description='Create GTFS from OpenStreetMap data.')

# Filename arguments for config and output file
parser.add_argument('--config', '-c', metavar='FILE',
                    type=argparse.FileType('r'), help='Configuration file')
parser.add_argument('--output', '-o', metavar='FILENAME',
                    type=str, help='Specify GTFS output zip file')

# Refresh caching arguments
group = parser.add_mutually_exclusive_group()
group.add_argument('--refresh-routes', action="store_true",
                   help='Refresh OSM data for all routes')
group.add_argument('--refresh-stops', action="store_true",
                   help='Refresh OSM data for all stops')
group.add_argument('--refresh-schedule-source', action="store_true",
                   help='Refresh data for time information')
group.add_argument('--refresh-all', action="store_true",
                   help='Refresh all OSM data')
args = parser.parse_args()


def main():

    # Load, prepare and validate configuration
    config = Configuration(args)

    # Initiate OpenStreetMap helper containing data
    data = OsmConnector(config)

    # Refresh argument option calls
    if args.refresh_routes:
        data.get_routes(refresh=True)
    elif args.refresh_stops:
        data.get_stops(refresh=True)
    elif args.refresh_schedule_source:
        config.get_schedule_source(refresh=True)
    elif args.refresh_all:
        data.get_routes(refresh=True)
        data.get_stops(refresh=True)

    # Define (transitfeed) object for GTFS creation
    feed = transitfeed.Schedule()

    # Initiate creators for GTFS components through an object factory
    factory = CreatorFactory(config)
    agency_creator = factory.get_agency_creator()
    feed_info_creator = factory.get_feed_info_creator()
    routes_creator = factory.get_routes_creator()
    stops_creator = factory.get_stops_creator()
    schedule_creator = factory.get_schedule_creator()
    trips_creator = factory.get_trips_creator()

    # Add data to feed
    agency_creator.add_agency_to_feed(feed)
    feed_info_creator.add_feed_info_to_feed(feed)
    routes_creator.add_routes_to_feed(feed, data)
    stops_creator.add_stops_to_feed(feed, data)
    schedule_creator.add_schedule_to_data(data)
    trips_creator.add_trips_to_feed(feed, data)

    # Validate GTFS
    feed.Validate(transitfeed.ProblemReporter())

    # Write GTFS
    feed.WriteGoogleTransitFeed(config.output)

    # Add feed_info.txt to GTFS
    add_feed_info(feed, config.output)

    sys.exit()


# noinspection PyProtectedMember
def add_feed_info(feed, output_file):
    """
    Add feed_info.txt file to GTFS
    Workaround for https://github.com/google/transitfeed/issues/395
    """
    if 'feed_info' not in feed._table_columns:  # pylint: disable=protected-access
        return

    with transitfeed.zipfile.ZipFile(output_file, 'a') as archive:
        feed_info_string = transitfeed.StringIO.StringIO()
        writer = transitfeed.util.CsvUnicodeWriter(feed_info_string)
        columns = feed.GetTableColumns('feed_info')
        writer.writerow(columns)
        writer.writerow([transitfeed.util.EncodeUnicode(feed.feed_info[c]) for c in columns])
        # pylint: disable=protected-access
        feed._WriteArchiveString(archive, 'feed_info.txt', feed_info_string)


if __name__ == "__main__":
    main()
