from event import Event
from packet import DataPacket
from packet import AckPacket
from event_queue import EventQueue

import constants
import math
import queue

class FlowFast:
    """Flow Class"""
    def __init__(self, ID, source, destination, data_amt, start):
        self.ID = ID                # Flow ID

        self.source = source        # Source host
        self.dest = destination     # Destination host
        self.data_amt = data_amt    # Size of data in MB
        self.start = start          # Time at which flow begins
        
        self.windowSize = 1.0       # set in congestion control algorithm
                                    # initialize to 1 for RENO and FAST

        self.done = False

        # Number of data packets the flow needs to send
        self.num_packets = math.ceil(data_amt * constants.MB_TO_BYTES / \
            constants.DATA_PKT_SIZE)

        # Packet that we will send next, if this is equal to num_packets
        #   then we have attempted to send all packets. Packets should now be
        #   sent from dropped array, if there are no packets there, we are
        #   done. 


        self.minRTT = 0.0
        self.numRTT = 0.0
        self.sumRTT = 0.0
        self.gamma = 0.5
        self.alpha = 15

        # TCP Reno and Fast TCP stuff
        self.unackPackets = []  
        self.last_unackd = 0  
        self.dupAckCtr = 0
        self.unreceivedpackets = []
        self.timeouts_to_cancel = []
        self.timeout_ctr = 0

        # TCP Reno Stuff Only 
        # Slow start threshold (max buffer size converted to data packets)
        self.sst = 1000000

    def flowReceiveDataPacket(self, data_packet):
        '''
        When the flow receives a data packet, an acknowledgment packet is
        created and enqueued for the packet. 
        '''

        if data_packet.packet_id in self.unreceivedpackets:
            self.unreceivedpackets.remove(data_packet.packet_id)

        if len(self.unreceivedpackets) > 0:
            # Update expected ACK ID
            next_expected_packet = self.unreceivedpackets[0]  
        else:
            next_expected_packet = self.num_packets

        # Create and send an acknowledgement packet
        #print("Sending ACK packet ID %d for data packet ID %d" %(next_expected_packet, data_packet.packet_id))
        ackpckt = AckPacket(next_expected_packet, self.dest, \
            self.source, self.ID, data_packet.timestamp)
        self.sendPacket(ackpckt)

    def getACK(self, packetID, pktMadeTime):
        '''
        When an acknowledgment is received, the ID is checked against the
        counter of acknowledgments to check for dropped packets. 
        '''

        self.updateRTTandLogRTD(pktMadeTime)
        #print("Flow received an acknowledgement with ID %d" %packetID)
        #print("Last Unack'd: %d" %self.last_unackd)

        if packetID > self.last_unackd:
            self.last_unackd = packetID

            self.removeAckdPackets()

            if self.last_unackd == self.num_packets:
                self.unackPackets.clear()
                self.done = True
                print("Flow %s is done at time %s" % (self.ID, constants.system_EQ.currentTime))
                
                flow_done_event = Event(Event.flow_done, \
                    constants.system_EQ.currentTime, \
                    [constants.system_EQ.currentTime])
                constants.system_EQ.enqueue(flow_done_event)
                return

            lengthPktsToSend = math.ceil(self.windowSize)\
             - len(self.unackPackets)
            self.flowSendNPackets(lengthPktsToSend)


    ''' Functions for TCP Congestion Control ''' 
    def flowStart(self):
        '''
        Initializes the beginning of a flow by setting the list of unreceived 
        packets contain all the packets in order. Initial packets are then sent.
        '''

        for pkt_ID in range(self.num_packets):
            self.unreceivedpackets.append(pkt_ID)

        # Send initial packets
        self.flowSendNPackets(math.ceil(self.windowSize))
        
        FAST_event = Event(Event.update_FAST, constants.system_EQ.currentTime\
             + constants.FAST_PERIOD, [self.ID])
        constants.system_EQ.enqueue(FAST_event)


    def flowSendNPackets(self, N):
        '''
        Sends N packets from the packetsToSendQueue.
        '''

        #print("FlowSendNPackets: Sending %d packets" %N)
        num_packets_sent = 0       # list of packets to send

        for PID in range(self.last_unackd, self.last_unackd+N):
            if PID >= self.num_packets:
                break

            if PID not in self.unackPackets:    # Only send new packets
                pkt = DataPacket(PID, self.source, self.dest, self.ID, \
                    constants.system_EQ.currentTime)    # Create data packet
                self.sendPacket(pkt)
                num_packets_sent += 1

        # Log that packets were sent
        constants.system_analytics.log_flow_send_rate(self.ID, \
            num_packets_sent * constants.DATA_PKT_SIZE, \
            constants.system_EQ.currentTime)


    def handlePacketTimeout(self, packetID):
        '''
        This will be called by event handler in the case of a packet timeout.
        '''
        # If packet is unacknowledged
        if packetID in self.unackPackets and \
            packetID not in self.timeouts_to_cancel:    
            #print("Got timeout event for packet %d" % packetID)
            self.timeout_ctr += 1
            # Remove packet from unacknowledged packets
            self.unackPackets.remove(packetID)         

            pkt = DataPacket(packetID, self.source, self.dest, self.ID, \
                    constants.system_EQ.currentTime)
            self.sendPacket(pkt)

        if packetID in self.timeouts_to_cancel:
            self.timeouts_to_cancel.remove(packetID)


    def updateW(self):
        '''
        Window size is recalculated based on the fast TCP algorithm. 
        '''
        if self.numRTT == 0:
            self.windowSize = 1
        else:
            avgRTT = float(self.sumRTT)/float(self.numRTT)
            doubW = 2 * self.windowSize
            eqW = (1-self.gamma) * float(self.windowSize) + self.gamma * \
                    float(self.minRTT/avgRTT * self.windowSize + self.alpha)
            self.windowSize = min(doubW, eqW)

        self.logWindowSize()

        # Enqueue an event to update Fast TCP W after certain time
        if self.done == False:
            FAST_event = Event(Event.update_FAST,
                                constants.system_EQ.currentTime \
                                    + constants.FAST_PERIOD, [self.ID])
            constants.system_EQ.enqueue(FAST_event)


    def updateRTTandLogRTD(self, pktMadeTime):
        '''
        The round trip time and round trip delay is calculated based on packet
        attributes.
        '''
        RTT = constants.system_EQ.currentTime - pktMadeTime
        constants.system_analytics.log_packet_RTD(self.ID,
            RTT, constants.system_EQ.currentTime)

        if self.minRTT == 0:        # Save minimum RTT time
            self.minRTT = RTT
        elif RTT < self.minRTT:
            self.minRTT = RTT
        # CHECK: is average only over current time period or over whole time
        self.sumRTT += RTT
        self.numRTT += 1.0

    def sendPacket(self, pkt):
        '''
        The flow enqueues a packet 
        '''
        if type(pkt) is DataPacket:
            #print("Sending DATA packet ID %d" %pkt.packet_id)
            self.unackPackets.append(pkt.packet_id)

            # Calculate the time at which to timeout
            timeout_time = constants.system_EQ.currentTime \
                        + constants.TIMEOUT_TIME

            # Create and enqueue timeout event
            timeout_ev = Event(Event.pckt_timeout, timeout_time, [pkt])
            constants.system_EQ.enqueue(timeout_ev)
            event_to_send = Event(Event.flow_send_packets, \
                    constants.system_EQ.currentTime, [self.source, [pkt]])

        else:
            event_to_send = Event(Event.flow_send_packets, \
                        constants.system_EQ.currentTime, [self.dest, [pkt]])
            #print("Sending ACK packet ID %d" %pkt.packet_id)

        constants.system_EQ.enqueue(event_to_send)
    
    def removeAckdPackets(self):
        ''' 
        Iterates through the list of unacknowledged packets. If the packet
        ID is already acknowledged and thus a smaller value than the last 
        unacknowledged packet ID, it will be removed from the list. 
        '''
        cur_length = len(self.unackPackets)
        for PID in self.unackPackets:
            if PID < self.last_unackd:
                self.unackPackets.remove(PID)
        return (len(self.unackPackets)-cur_length)

    def logWindowSize(self):
        ''' 
        Calls analytics to record the current window size of the flow. 
        '''
        constants.system_analytics.log_window_size(self.ID, \
            constants.system_EQ.currentTime, self.windowSize)




