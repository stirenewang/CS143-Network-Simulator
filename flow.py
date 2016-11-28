from event import Event
from packet import DataPacket
from event_queue import EventQueue
import constants
import math
class Flow:
    """Flow Class"""
    def __init__(self, ID, source, destination, data_amt, start):
        self.ID = ID                # Flow ID

        self.source = source        # Source host
        self.dest = destination     # Destination host
        self.data_amt = data_amt    # Size of data in MB
        self.start = start          # Time at which flow begins
        
        self.windowSize = 25        # set in congestion control algorithm 
        self.currACK = -1            # the last acknowledged packet ID
        self.droppedPackets = []    # dropped packets (IDs)

        # Number of data packets the flow needs to send
        self.num_packets = math.ceil(data_amt * constants.MB_TO_BYTES / constants.DATA_PKT_SIZE)

        # Packet that we will send next, if this is equal to num_packets
        #   then we have attempted to send all packets. Packets should now be
        #   sent from dropped array, if there are no packets there, we are
        #   done. 
        self.currPCK = 0

        self.pkt_entry_times = {}

        self.minRTT = 0


    def congestionControlAlg(pcktReceived, pcktSent): 
        # run congestion control alg
        # TCP Reno
        # FAST-TCP
        self.windowSize = 100
        constants.system_analytics.log_window_size(self.ID, constats.system_EQ.currentTime, self.windowSize)
        #return self.windowSize

    ''' Sends a list of packets depending on the windowSize to the host. The
        function sends packets from dropped packets and new packets (gives 
        dropped packets priority). If there are not enough packets, the
        function sends whatever packets it can. '''
    def flowSendPackets(self): 
        packets_to_send = []
        if constants.debug: 
            print("Currently in Flow send Packets: ")
            print("dropped Packets: %s, WindowSize: %s" % (self.droppedPackets, self.windowSize))

        if self.currACK == self.num_packets - 1 and self.droppedPackets == []: # We're done with this flow...YAY!
            return
        # Send ALL packets from dropped packets
        if len(self.droppedPackets) >= self.windowSize:
            packets_to_send = self.generateDataPackets(self.droppedPackets[:(self.windowSize)])

        # send SOME (could be 0) packets from dropped packets and SOME from new packets
        else:
            # Generate and get ready to send packets from dropped packets
            getPcktsToSend = self.generateDataPackets(self.droppedPackets)
            packets_to_send.extend(getPcktsToSend)

            # Generate and get ready to send new packets
            temp = self.windowSize - len(self.droppedPackets)

            # If we reach the end of all the packets to send
            if self.currPCK + temp >= self.num_packets:
                end_pckt_index = self.num_packets + 1   # Indicate we have sent all packets
            else:   # Otherwise
                end_pckt_index = self.currPCK + temp
            if constants.debug: print("Generating data packets in range: %s to %s" %(self.currPCK, end_pckt_index))
            getPcktsToSend = self.generateDataPackets(range(self.currPCK, end_pckt_index))
            packets_to_send.extend(getPcktsToSend)

            # Update the current packet we want to send
            self.currPCK = end_pckt_index

        # Enqueue event that will tell hosts to send packets
        if constants.debug: print("Event is getting enqueued...")
        event_to_send = Event(Event.flow_src_send_packets, constants.system_EQ.currentTime, [self.source, packets_to_send])
        constants.system_EQ.enqueue(event_to_send)
        if constants.debug: 
            print("\tevent type: %s" % event_to_send.event_type)
            print("\tevent time: %s" % event_to_send.time)
            print("\tevent data: %s" % event_to_send.data)
            print("\tLen of eventlist: %s" % len(constants.system_EQ.eventList))

        constants.system_analytics.log_flow_send_rate(self.ID, self.windowSize, constants.system_EQ.currentTime)

    ''' When a host receives an acknowledgement packet it will call this 
        function for the flow to update what packets have been received. The 
        flow deals with packet loss.'''
    def getACK(self, packetID, ackTime):

        constants.system_analytics.log_packet_RTD(self.ID, self.pkt_entry_times[packetID], ackTime)
        RTT = constants.system_EQ.currentTime - self.pkt_entry_times[packetID]
        if self.minRTT == 0:
        	minRTT = RTT
        elif RTT < minRTT:
        	minRTT = RTT
        del self.pkt_entry_times[packetID]

        if packetID == 0:
        	print("First ack")
        	print(constants.system_EQ.currentTime)
        
        if packetID  > self.currACK+1:  # if we dropped a packet
            # Add the packets we dropped to the droppedPackets list
            self.droppedPackets.append(range(self.currACK+1, packetID))
            self.currACK += 1
        elif packetID < self.currACK:   # If we receive an ack for packet that was dropped
            # Remove this packet from list of dropped packets
            self.droppedPackets.remove(packetID)
        else:
            self.currACK += 1   # We received correct packet, increment currACK

        if (self.currACK - len(self.droppedPackets) + 1) % self.windowSize == 0: # We're finished with this window; send a new one
            self.flowSendPackets()

        

    ''' Generates data packets with the given IDs and returns a list of the 
        packets. '''
    def generateDataPackets(self, listPacketIDs):
        packets_list = []
        if constants.debug: print("Generating Data Packets...")
        for PID in listPacketIDs:
            pckt = DataPacket(PID, self.source, self.dest, self.ID)
            packets_list.append(pckt)
            if pckt.packet_id not in self.pkt_entry_times:
                self.pkt_entry_times[pckt.packet_id] = constants.system_EQ.currentTime

        return packets_list



