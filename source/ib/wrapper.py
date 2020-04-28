from ibapi.wrapper import (EWrapper, ListOfHistoricalTick,
    ListOfHistoricalTickBidAsk, ListOfHistoricalTickLast)
from .finishable_queue import FinishableQueue, Status as QStatus

import queue
import typing

class IBError(Exception):
    """
    Error object to handle the error retruns from IB
    """

    def __init__(self, id: int, errorCode: int, errorString: str):
        self.id = id
        self.errorCode = errorCode
        self.errorString = errorString

        super().__init__(errorString)

    def __str__(self):
        # override method
        error_msg = "IB error id %d errorcode %d string %s" \
            % (self.id, self.errorCode, self.errorString)

        return error_msg

class IBWrapper(EWrapper):
    """
    The wrapper deals with the action coming back from the IB gateway or 
    TWS instance
    """

    __contract_details_queue = {}
    __head_timestamp_queue = {}
    __historical_ticks_data_queue = {}

    def __init__(self):
        self.__err_queue = queue.Queue()

        super().__init__()

    # Error handling
    def has_err(self):
        return not self.__err_queue.empty()
 
    def get_err(self, timeout=10):
        if self.has_err():
            try:
                return self.__err_queue.get(timeout=timeout)
            except queue.Empty:
                return None

        return None
       
    def error(self, id, errorCode, errorString):
        # override method
        err = IBError(id, errorCode, errorString)
        
        self.__err_queue.put(err)

    # Get contract details
    def init_contract_details_queue(self, reqId):
        self.__contract_details_queue[reqId] = queue.Queue()

        return self.__contract_details_queue[reqId]

    def contractDetails(self, reqId, contractDetails):
        # override method
        if reqId not in self.__contract_details_queue.keys():
            self.init_contract_details_queue(reqId)

        self.__contract_details_queue[reqId].put(contractDetails)

    def contractDetailsEnd(self, reqId):
        # override method
        if reqId not in self.__contract_details_queue.keys():
            self.init_contract_details_queue(reqId)

        self.__contract_details_queue[reqId].put(QStatus.FINISHED)

    # Get earliest data point for a given instrument and data
    def init_head_timestamp_queue(self, req_id: int):
        self.__head_timestamp_queue[req_id] = queue.Queue()

        return self.__head_timestamp_queue[req_id]

    def headTimestamp(self, reqId: int, headTimestamp: str):
        # override method
        if reqId not in self.__head_timestamp_queue.keys():
            self.init_contract_details_queue(reqId)

        self.__head_timestamp_queue[reqId].put(headTimestamp)
        self.__head_timestamp_queue[reqId].put(QStatus.FINISHED)

    # Fetch historical ticks data
    def init_historical_ticks_data_queue(self, req_id: int) -> queue.Queue:
        self.__historical_ticks_data_queue[req_id] = queue.Queue()

        return self.__historical_ticks_data_queue[req_id]

    def historicalTicks(
        self, reqId: int, ticks: ListOfHistoricalTick, done: bool
    ):
        # override method
        self.__handle_historical_ticks_results(reqId, ticks, done)

    def historicalTicksBidAsk(
        self, reqId: int, ticks: ListOfHistoricalTickBidAsk, done: bool
    ):
        # override method
        self.__handle_historical_ticks_results(reqId, ticks, done)

    def historicalTicksLast(
        self, reqId: int, ticks: ListOfHistoricalTickLast, done: bool
    ):
        # override method
        self.__handle_historical_ticks_results(reqId, ticks, done)
        
    ## Private functions
    def __handle_historical_ticks_results(
        self,
        req_id: int,
        ticks: typing.Union[
            ListOfHistoricalTick,
            ListOfHistoricalTickBidAsk,
            ListOfHistoricalTickLast
        ],
        done: bool
    ):
        """
        Handles results return from functions `historicalTicks`, 
        `historicalTicksBidAsk`, and `historicalTicksLast` by putting the 
        results into corresponding queue & marks the queue as finished.
        """

        if req_id not in self.__historical_ticks_data_queue.keys():
            self.init_historical_ticks_data_queue(req_id)

        self.__historical_ticks_data_queue[req_id].put(ticks)
        self.__historical_ticks_data_queue[req_id].put(done)
        self.__historical_ticks_data_queue[req_id].put(QStatus.FINISHED)
