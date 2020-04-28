from ibapi.contract import Contract
from ibapi.client import EClient
from .wrapper import IBWrapper, IBError
from .finishable_queue import FinishableQueue, Status as QStatus

import enum

class Const(enum.Enum):
    MAX_WAIT_SECONDS = 10
    MSG_TIMEOUT = "Exceed maximum wait for wrapper to confirm finished"

class IBClient(EClient):
    """
    The client calls the native methods from IBWrapper instead of 
    overriding native methods
    """

    def __init__(self, wrapper: IBWrapper):
        self.__wrapper = wrapper
        super().__init__(wrapper)

    def resolve_contract(self, contract: Contract, req_id: int) -> Contract:
        """
        From a partially formed contract, returns a fully fledged version
        :returns fully resolved IB contract
        """

        # Make place to store the data that will be returned
        contract_details_queue = FinishableQueue(
            self.__wrapper.init_contract_details_queue(req_id)
        )

        print("Getting full contract details from IB...")

        self.reqContractDetails(req_id, contract)

        # Run until we get a valid contract(s) or timeout
        new_contract_details = contract_details_queue.get(
            timeout=Const.MAX_WAIT_SECONDS.value
        )

        try:
            self.__check_error()
        except IBError as err:
            print(err)

        if contract_details_queue.get_status() == QStatus.TIMEOUT:
            print(Const.MSG_TIMEOUT.value)

        if len(new_contract_details) == 0:
            print("Failed to get additional contract details: returning unresolved contract")
            
            return contract

        if len(new_contract_details) > 1:
            print("Multiple contracts found: returning 1st contract")

        resolved_contract = new_contract_details[0].contract

        return resolved_contract

    def resolve_head_timestamp(
        self, contract: Contract, ticker_id: int, unix_time: bool = False
    ) -> str:
        """
        Fetch the earliest available data point for a given instrument from IB.

        :returns timestamp in TWS/IB Gateway timezone specified at login or 
        unix time
        """
        queue = FinishableQueue(
            self.__wrapper.init_head_timestamp_queue(ticker_id)
        )

        print("Getting earliest available data point for the given instrument from IB... ")

        self.reqHeadTimeStamp(
            ticker_id, contract, "TRADES", 1, 2 if unix_time else 1
        )

        head_timestamp=queue.get(timeout=Const.MAX_WAIT_SECONDS.value)

        try:
            self.__check_error()
        except IBError as err:
            print(err)

        if queue.get_status() == QStatus.TIMEOUT:
            print(Const.MSG_TIMEOUT.value)

        if len(head_timestamp) == 0:
            print("Failed to get the earliest available data point")

            return None

        if len(head_timestamp) > 1:
            print("[Abnormal] Multiple result received: returning 1st result")

        return head_timestamp[0]

    # Private functions
    def __check_error(self):
        """
        Check if the error queue in wrapper contains any error returned from IB
        """
        while self.__wrapper.has_err():
            err: IBError = self.__wrapper.get_err()

            if err.id == -1:
                # -1 means a notification not error
                continue
            else:
                raise err
