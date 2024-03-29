import argparse
from datetime import date
import json
import logging
import os
from pprint import pformat

import config
import csv_util
import dms_util


LOGGER = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)


def get_env_var(env_var_name):
    env_var = ""
    if env_var_name in os.environ:
        env_var = os.environ[env_var_name]
    else:
        print('get_env_var: Failed to get %s' % env_var_name)
    return env_var


def get_env_vars():
    config.dest_bucket_name = get_env_var("DEST_BUCKET_NAME")
    if config.dest_bucket_name == "":
        print("get_env_vars: failed to retrieve DEST_BUCKET_NAME.")
        return False
        
    config.region_name = get_env_var("REGION_NAME")
    if config.region_name == "":
        print("get_env_vars: failed to retrieve REGION_NAME.")
        return False
        
    # DEBUG
    print("get_env_vars:")
    print("dest_bucket_name: %s" % (config.dest_bucket_name))
    print("region_name: %s" % (config.region_name))
    
    return True


def get_event_vars(event):
    # DMS erplication task id
    config.replication_task_id = ""
    dms_event_str = event['Records'][0]['Sns']['Message']
    print("[DEBUG] get_event_vars: DMS event string = %s" % dms_event_str)
    dms_event = json.loads(dms_event_str)
    print("[DEBUG] get_event_vars: DMS event = %s" % dms_event)
    config.replication_task_id = dms_event['SourceId']
    
    # initialize DMS replication task ARN
    config.replication_task_arn = ""
    
    # DEBUG
    print("get_event_vars:")
    print("replication_task_id: %s" % (config.replication_task_id))
    print("replication_task_arn: %s" % (config.replication_task_arn))
    
    return True
    
    
def lambda_handler(event, context):
    # start
    print('\nStarting lambda_function.lambda_handler ...')
    LOGGER.info("%s", pformat({"Context" : context, "Request": event}))
    
    # get environment variables
    if get_env_vars() == False:
        print("dms-replication-task-event: get_env_vars() failed.")
        return False
        
    # get event variables
    if get_event_vars(event) == False:
        print("dms-replication-task-event: get_event_vars() failed.")
        return False
        
    # check if replication task status is now stopped
    task_status = dms_util.get_task_status(config.replication_task_id)
    if task_status == 'stopped':
        # get table stats
        print("dms-replication-task-event: Task %s is stopped. Getting table stats ..." % (config.replication_task_arn))
        table_stats = dms_util.get_table_stats(config.replication_task_arn)
        print("dms-replication-task-event: Printing table stats for task %s ..." % (config.replication_task_arn))
        print("==")
        print("DEBUG")
        print("==")
        print(table_stats)
        print("==")
    
        # set dest_object_prefix and dest_object_name
        task_id = config.replication_task_id
        today = date.today()
        dest_object_prefix = "task_id="+task_id+"/"+"date="+str(today)+"/"
        dest_object_name = "table_stats.csv"
        
        print("dms-replication-task-event: Writing and uploading table stats as:")
        print("dest_bucket_name: %s" % (config.dest_bucket_name))
        print("dest_object_prefix: %s" % (dest_object_prefix))
        print("dest_object_name: %s" % (dest_object_name))
        
        # write csv file
        csv_util.write_csv_file(table_stats, dest_object_name)
        
        # upload csv file to dest bucket
        csv_util.put_csv_file_as_s3_object(config.dest_bucket_name, dest_object_prefix, dest_object_name)
    else:
        print("dms-replication-task-event: Task %s is %s." % (config.replication_task_arn, task_status))

    # end
    print('\n... Thaaat\'s all, Folks!')


if __name__ == '__main__':
    # read arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-t", "--test-event", required=True, help="Test event.")
    args = vars(ap.parse_args())
    print("dms-replication-task-event: args = %s" % (args))

    # load json file
    test_event_file_name = args['test_event']
    f = open(test_event_file_name)
    event = json.load(f)
    f.close()
    print("dms-replication-task-event: test_event = %s" % (event))

    # create test context
    context = {}

    # Execute test
    lambda_handler(event, context)

