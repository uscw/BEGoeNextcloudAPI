# BEGoeNextcloudAPI

This python code is used to create users in a Nextcloud via batch operation.

For a quick survey it maintains additionally a local user DB.

## Usage:

Output of ```python nextcloud_begoe_api.py -h```:


```
python nextcloud_begoe_api.py [-h] [-v | -q] [-i [GET_NEXTCLOUD_INFO]]
                              [-l [GET_LOCAL_CSV_INFO]] [-a [ADD_USER_FROM_CSV_INFO]]
                              [-A [ADD_USER_FROM_PARAMETER]]
                              [-d [DELETE_USER_FROM_NEXTCLOUD]]
                              [-s [SYNCHRONIZE_USERS_FROM_NEXTCLOUD]]

nextcloud administration tool for BEGö team environment

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose
  -q, --quiet
  -i [GET_NEXTCLOUD_INFO], --get_nextcloud_info [GET_NEXTCLOUD_INFO]
                        get user and group info from nextcloud
  -l [GET_LOCAL_CSV_INFO], --get_local_csv_info [GET_LOCAL_CSV_INFO]
                        get user and group info from local csv file
  -a [ADD_USER_FROM_CSV_INFO], --add_user_from_csv_info [ADD_USER_FROM_CSV_INFO]
                        add user from local csv file
  -A [ADD_USER_FROM_PARAMETER], --add_user_from_parameter [ADD_USER_FROM_PARAMETER]
                        add user from parameter object
  -d [DELETE_USER_FROM_NEXTCLOUD], --delete_user_from_nextcloud [DELETE_USER_FROM_NEXTCLOUD]
                        delete user from nextcloud
  -s [SYNCHRONIZE_USERS_FROM_NEXTCLOUD], --synchronize_users_from_nextcloud [SYNCHRONIZE_USERS_FROM_NEXTCLOUD]
                        synchronize users from nextcloud to local user csv

```

