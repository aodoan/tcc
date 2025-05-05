"""
Contain all the configuration of the IDS 
"""

db_file = "./ids/incoming_packets.csv"
sleep_time = 0.01

drop_duplicates = True # Whether or not duplicate in the dataset should be removed
convert_labels = True # Convert all normal trafic to 0 and all atacks to 1
oversample = False # Whethe or not oversample should be used in the dataset
datasets = ["kdd99"]

features = {
    "kdd99": {
        "features": {
            "duration": "continuous",
            "protocol_type": "symbolic",
            "service": "symbolic",
            "flag": "symbolic",
            "src_bytes": "continuous",
            "dst_bytes": "continuous",
            "land": "symbolic",
            "wrong_fragment": "continuous",
            "urgent": "continuous",
            "hot": "continuous",
            "num_failed_logins": "continuous",
            "logged_in": "symbolic",
            "num_compromised": "continuous",
            "root_shell": "continuous",
            "su_attempted": "continuous",
            "num_root": "continuous",
            "num_file_creations": "continuous",
            "num_shells": "continuous",
            "num_access_files": "continuous",
            "num_outbound_cmds": "continuous",
            "is_host_login": "symbolic",
            "is_guest_login": "symbolic",
            "count": "continuous",
            "srv_count": "continuous",
            "serror_rate": "continuous",
            "srv_serror_rate": "continuous",
            "rerror_rate": "continuous",
            "srv_rerror_rate": "continuous",
            "same_srv_rate": "continuous",
            "diff_srv_rate": "continuous",
            "srv_diff_host_rate": "continuous",
            "dst_host_count": "continuous",
            "dst_host_srv_count": "continuous",
            "dst_host_same_srv_rate": "continuous",
            "dst_host_diff_srv_rate": "continuous",
            "dst_host_same_src_port_rate": "continuous",
            "dst_host_srv_diff_host_rate": "continuous",
            "dst_host_serror_rate": "continuous",
            "dst_host_srv_serror_rate": "continuous",
            "dst_host_rerror_rate": "continuous",
            "dst_host_srv_rerror_rate": "continuous",
            "label" : "symbolic"
        },
        "normal_traffic" : "normal."
    }
}
