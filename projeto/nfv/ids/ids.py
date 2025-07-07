"""
This file contain the implementantion of a IDS (Intrusion Detection System)

"""
import logging
import threading
import time
import json
from datetime import datetime
import ids.internal_configuration as ids_internal_config
from ids.configuration.config import IDSConfig
from ids.oad import OAD
from ids.methods.anomaly_detection import AnomalyDetector

class IDS:
    """
        Description of elements:

        OAD: Is responsible for the comunication between the IDS and the NFV
        Also, is reponsible for packaging sniffer

        Store Data: Is responsible for store all the data into a database

        Configuration: Contain the internal configuration of the IDS 
            - Can be changed by the NFVO trough the OAD module

        Reference Data: Internal structure of expected behaviours of entities (or known attacks)

        Processing: Is responsible to process incoming packets and according to the
        Configuration module + Reference Data, it decides whether is an intrusion or not 


        Alarm: Is responsible of notify OAD of intrusions detected by Processing module

        Performance: Is an extra module that calculate the number 
    """
    def __init__(self, driver):
        """Initialize necessary structures and setup RabbitMQ communication"""
        self.driver = driver

        self.db_file = open(ids_internal_config.db_file, "a+")

        #self.detector = AnomalyDetector(method="if")
        self.detector = None
        self.start_summary()

    def start_summary(self):
        self.summary = {
            "n_packets": 0, # Total number of packages analyzed by the Detector
            "t_positives": 0,    # intrusions correctly detected
            "t_negatives": 0,    # normal traffic correctly identified
            "f_positives": 0,    # normal traffic incorrectly flagged as intrusion
            "f_negatives": 0,    # intrusions that were not detected
        }

    def start_monitoring(self):
        """Start monitoring with the driver"""
        # First, create a thread to receive messages
        get_packets_thread = threading.Thread(target=self.__get_packets)
        get_packets_thread.daemon = True
        get_packets_thread.start()
        
        # Call start_driver (blocking)
        self.driver.start_driver()

    def interface(self, msg):
        action = msg["action"]
        if action == "train":
            logging.info("Training with method: %s.", msg["method"])
            if self.detector is not None:
                logging.warning("The detector is already trained. Erasing old model")
                self.detector = None
            self.start_summary()
            start_time = datetime.now()
            self.detector = AnomalyDetector(method=msg["method"],
                                            dataset_name=msg["dataset"]) 
                                            
            self.detector.train_model(argument=msg["argument"])
            # Done training, send message to queue
            end_time = datetime.now()
            runtime = str(end_time - start_time)

            ret = {
                "status": "training done",
                "runtime": runtime
            }
            self.driver.send_message(json.dumps(ret), control=True, queue=msg["rqueue"])

        elif action == "fetch_summary":
            print(self.summary)
            ret = self.fetch_summary()
            self.driver.send_message(ret, control = True, queue=msg["rqueue"])
            logging.info("Sending summary back to %s.", msg["rqueue"])
        elif action == "clean_summary":
            self.start_summary()
            ret = "ok"
            self.driver.send_message(ret, control = True, queue=msg["rqueue"])
            logging.info("Cleaning summary")
        elif action == "clear_model":
            if self.detector is None:
                logging.warning("No model set.")
            else:
                logging.info("Cleaning current model.")
                self.detector = None
        else:
            logging.error("Unknown action. [%s]", msg)

    def __get_packets(self):
        """Internal thread used to fetch packages from the driver recv queue"""
        while True:
            # get_packet is a non-blocking call implemented by the OAD
            packet = self.driver.get_packet()

            control_packet = self.driver.get_control_packet()

            if control_packet:
                self.interface(control_packet)

            if packet:
                self.process(packet)
            else:
                time.sleep(ids_internal_config.sleep_time)

    def store_data(self, packet):
        """ Store a data obtained from the OAD for future referecing """
        self.db_file.write(packet)
        self.db_file.flush()
        pass

    def alarm(self, message):
        """ 
        Notify OAD that an Intrusion ocurred

        Args:
            message(str): A string in JSON format to be sent to the MANO
        """
        logging.info("DETECTED AN INTRUSION")
        self.driver.send_message(message)

    def process(self, package):
        """ 
        Process a package. If it is an intrusion, notify the NFVO trough the OAD
        Args:
            package(bytes): A package in bytes format
        """
        print("analyzing packet")
        package = package.decode("utf-8")
        # First step, is to store data for future referencing
        self.store_data(package)

        # Then, analyze the data
        ret = self.analyze(package)
        if ret is True:
            message = {
                "action" : "alarm",
                "package": package
            }

            self.alarm(json.dumps(message))


    def analyze(self, package):
        """
            Process a package and return True if it's an Intrusion
            
            Args:
                package(str): 
        """
        print("Analyzing packet.")
        if self.detector is None:
            logging.warning("Got data but no model is set!")
            return

        predicted_label, actual_label = self.detector.predict_instance(package)
        self.count(predicted_label, actual_label)
        print(predicted_label, actual_label)


        

    def configuration(self):
        """Handle internal configuration"""
        pass

    def count(self, preditect_label, correct_label):
        self.summary["n_packets"] += 1
        if preditect_label == -1:
            if correct_label == -1:  # True Positive
                self.summary["t_positives"] += 1
            else:  # False Positive
                self.summary["f_positives"] += 1
        else:
            if correct_label == -1:  # False Negative
                self.summary["f_negatives"] += 1
            else:  # True Negative
                self.summary["t_negatives"] += 1

    def __accuracy(self):
        vp = self.summary["t_positives"]
        vn = self.summary["t_negatives"]
        fp = self.summary["f_positives"]
        fn = self.summary["f_negatives"]
        if (vp + vn + fp + fn) != 0.0:
            return (vp+vn)/(vp+vn+fp+fn)
        logging.warning("Cannot calculate accuracy: No packages identified")
        return 0.0

    def __detection_rate(self):
        vp = self.summary["t_positives"]
        vn = self.summary["t_negatives"]
        if (vp + vn) != 0.0:
            return vp / (vp + vn)
        logging.warning("Cannot calculate detection rate: No packages identified")
        return 0.0
    
    def __false_alarm(self):
        vn = self.summary["t_negatives"]
        fp = self.summary["f_positives"]
        if (fp + vn) != 0.0:
            return fp / (fp + vn)
        logging.warning("Cannot calculate false alarm rate: No packages identified")
        return 0.0

    def fetch_summary(self):
        msg = {
            "n_packages": self.summary["n_packets"],
            "accuracy": self.__accuracy(),
            "detection_rate": self.__detection_rate(),
            "false_alarm": self.__false_alarm(),
            "t_positives":self.summary["t_positives"],
            "t_negatives":self.summary["t_negatives"],
            "f_positives":self.summary["f_positives"],
            "f_negatives":self.summary["f_negatives"]
        }
        return json.dumps(msg, indent=4)


if __name__ == "__main__":
    logging.basicConfig(
        filename="logs/ids.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    driver = OAD() 
    ids = IDS(driver)
    ids.start_monitoring()
