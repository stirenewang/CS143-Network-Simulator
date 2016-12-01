import constants
import matplotlib.pyplot as plt
import collections

class Analytics:

    def __init__(self, outFile):
        time_step = []      # Holds the time step (from global time variable)
                            #   at which data was recorded
                            # Do we need this?

        '''
        The data types below are dictionaries with:
            keys: Link IDs (strings)
            values: list of tuples containing link information specific to
                the dictionary and the associated time
        '''
        self.link_buff_occupancy = {}    # Stores buffer occupancy (number of
                                    #   packes in the buffer at the time).
                                    #   Updated any time packet is added to
                                    #   any link buffer
        self.link_packet_lost = {}       # Stores number of packets lost. Updated
                                    #   every time a packet is added to a
                                    #   full buffer
        self.link_flow_rate = {}         # Stores number of packets sent over a
                                    #   link. Updates every time a packet 
                                    #   receive event occurs.

        # Still need per flow: send/receive rate, packet round trip delay
        self.flow_rate = {}
        self.flow_send_rate = {}
        self.flow_packet_RTD = {}
        self.flow_window_size = {}

        # and per host: send/receive rate
        self.host_send_rate = {}
        self.host_receive_rate = {}

        # not sure how to implement/compute these
        # file that we are writing to
        self.outFile = outFile
        self.pckts = 0

    '''This logs that this link dropped a packet at the current time.'''
    def log_dropped_packet(self, linkID, currTime, numPkts):
        if linkID in self.link_packet_lost:
            if currTime in self.link_packet_lost[linkID]:
                self.link_packet_lost[linkID][currTime] += numPkts
            else:
                self.link_packet_lost[linkID][currTime] = numPkts
        else:
            self.link_packet_lost[linkID] = {}
            self.link_packet_lost[linkID][currTime] = numPkts

    ''' Arrange dictionary by linkID followed by currTime'''
    def log_buff_occupancy(self, linkID, currTime, buffOccupancy):
        if linkID in self.link_buff_occupancy:
            self.link_buff_occupancy[linkID].append((currTime, buffOccupancy/constants.DATA_PKT_SIZE))
        else:
            self.link_buff_occupancy[linkID] = [(currTime, buffOccupancy/constants.DATA_PKT_SIZE)]

    ''' link flow rate calculation stores number of packets properly
    sent through flow in the span between current time to previous time'''
    # changed to flowID because I think this should be flow? i.e. when a flow
    # decides to put first packet in iink buffer to when host receives last
    # packet
    #def log_flow_rate(self, flowID, numBytes, currTime, prevTime):
    def log_flow_rate(self, flowID, numBytes, RTT, currTime): 
        rate = numBytes*constants.BYTES_TO_MBITS/(RTT/constants.SEC_TO_MS)
        if flowID in self.flow_rate:
            self.flow_rate[flowID].append((currTime, rate))
        else:
            self.flow_rate[flowID] = [(currTime, rate)]
        if constants.debug:
            print(rate)


    '''flow send rate should read the updating window sizes, which
    decide the send rate of each flow, and update it to the relevant time'''
    def log_flow_send_rate(self, flowID, windowSize, currTime):
        if flowID in self.flow_send_rate:
            self.flow_send_rate[flowID].append((windowSize, currTime))
        else:
            self.flow_send_rate[flowID] = [(windowSize, currTime)]

    '''flow receive rate should read the time that the packet was received
    at the host and add it to the corresponding packet in the flow'''
    def log_flow_receive_rate(self, flowID, currTime, receive_order):
        self.pckts += 1
        if flowID in self.flow_send_rate:
            # If the number of the received packet is greater than window size,
            #   there is an issue
            if constants.debug: print(self.flow_send_rate[flowID])
            if receive_order <= self.flow_send_rate[flowID][-1][0]:
                pass
                # Log the flow rate
                #self.log_flow_rate(flowID, constants.DATA_PKT_SIZE, currTime, self.flow_send_rate[flowID][-1][1])

    # time start is queued in immediately
    # time end is when the ack with the right packetID is sent
    # get the time for that ack in event queue
    def log_packet_RTD(self, flowID, timeStart, timeEnd):
        if flowID in self.flow_packet_RTD:
            self.flow_packet_RTD[flowID].append((timeEnd, timeEnd - timeStart))
        else:
            self.flow_packet_RTD[flowID] = [(timeEnd, timeEnd - timeStart)]


    def log_host_send_rate():
        pass

    def log_host_receive_rate():
        pass
        
    '''link rate should read the time that this delay was calculated for the 
    link and update the relevant link delay'''
    def log_link_rate(self, linkID, pktsize, duration, currTime):
        rate = pktsize * constants.BYTES_TO_MBITS/(duration/constants.SEC_TO_MS)

        if linkID[0:-1] in self.link_flow_rate:
            self.link_flow_rate[linkID[0:-1]].append((currTime, rate))
        else:
            self.link_flow_rate[linkID[0:-1]] = [(currTime, rate)]

    def log_window_size(self, flowID, currTime, windowSize):
        if flowID in self.flow_window_size:
            self.flow_window_size[flowID].append((currTime, windowSize))
        else:
            self.flow_window_size[flowID] = [(currTime, windowSize)]

    def generatePlots():
        pass

    def writeOutput(self):
        self.outFile.write("link buff occupancy: ")
        self.outFile.write(str(self.link_buff_occupancy))
        self.outFile.write("link packet lost:  ")
        self.outFile.write(str(self.link_packet_lost))
        self.outFile.write("link flow rate: ")
        self.outFile.write(str(self.link_flow_rate))
        self.outFile.write("\n\n\n\n Total Number of Packets: %d" % self.pckts)

    def plotOutput(self):
        fig, axes = plt.subplots(nrows=4, ncols=1)
        fig.tight_layout()
        colors = ['k', 'r', 'b', 'g', 'm', 'y', 'c', '0.5', '0.75', '#B62828',
        '#0F644D', '#87C41C']

        # Decide number of links to show based on test case number
        if constants.testcase in [0, 1]:
            num_plotted_links = 2
        else:
            num_plotted_links = 3

        color_ctr = 0
        plt.subplot(611)        # link rate plot
        sorted_linkIDs = sorted(self.link_flow_rate.keys())
        for linkID in sorted_linkIDs[:num_plotted_links]:
            if constants.debug:
                print("LINK FLOW RATE LINK ID:")
                print(linkID + " " + colors[color_ctr])
            #if list(self.link_flow_rate.keys()).index(linkID) is not 1:
            # Get time out of [time, rate] pairs
            time = [elt[0] for elt in self.link_flow_rate[linkID]]
            # Get rate out of [time, rate] pairs
            l_flow_rate_MBPS = [elt[1] for elt in self.link_flow_rate[linkID]]
            plt.plot(time, l_flow_rate_MBPS, label=linkID, marker='o', linestyle='--', markersize=1, color=colors[color_ctr], markeredgecolor=colors[color_ctr])
            color_ctr += 1

        plt.legend(bbox_to_anchor=(1,1))
        plt.xlabel('time (ms)')
        plt.ylabel('Link Rate (Mbps)')

        color_ctr = 0
        plt.subplot(612)        # buffer occupancy plot
        sorted_linkIDs = sorted(self.link_buff_occupancy.keys())
        for linkID in sorted_linkIDs[:num_plotted_links]:
            if constants.debug:
                print("LINK BUFF OCCUPANCY: ")
                print(linkID + " " + colors[color_ctr])
            time = [elt[0] for elt in self.link_buff_occupancy[linkID]]
            l_buff_occ_pkt = [elt[1] for elt in self.link_buff_occupancy[linkID]]
            plt.plot(time, l_buff_occ_pkt, label=linkID, marker='o', linestyle='--', markersize=1, color=colors[color_ctr], markeredgecolor=colors[color_ctr])
            color_ctr += 1

        plt.legend(bbox_to_anchor=(1,1))
        plt.xlabel('time (ms)')
        plt.ylabel('Buffer Occupancy (KB)')


        color_ctr = 0
        plt.subplot(613)
        '''
        #old
        time_RTD_list = list(self.flow_packet_RTD.values())
        time = [tup[0] for tup in time_RTD_list]
        pkt_RTD = [tup[1] for tup in time_RTD_list]
        plt.plot(time, pkt_RTD, color='k')
        plt.xlabel('time (ms)')
        plt.ylabel('Packet Delay (ms)')
        '''
        #new
        sorted_flowIDs = sorted(self.flow_packet_RTD.keys())
        for flowID in sorted_flowIDs:
            if constants.debug:
                print("PACKET DELAY FLOW ID:")
                print(flowID + " " + colors[color_ctr])
            #if list(self.link_flow_rate.keys()).index(linkID) is not 1:
            # Get time out of [time, delay] pairs
            time = [elt[0] for elt in self.flow_packet_RTD[flowID]]
            # Get delay out of [time, delay] pairs
            pkt_delay_S = [elt[1] for elt in self.flow_packet_RTD[flowID]]
            plt.plot(time, pkt_delay_S, label=flowID, marker='o', linestyle='--', markersize=1, color=colors[color_ctr], markeredgecolor=colors[color_ctr])
            color_ctr += 1

        plt.legend(bbox_to_anchor=(1,1))
        plt.xlabel('time (ms)')
        plt.ylabel('Packet Delay (ms)')

        plt.subplot(614)
        color_ctr = 0
        print(self.flow_rate)
        for flowID in self.flow_rate:
            time = [elt[0] for elt in self.flow_rate[flowID]]
            f_flow_rate = [elt[1] for elt in self.flow_rate[flowID]]
            print(time)
            print(f_flow_rate)
            plt.plot(time, f_flow_rate, label=flowID, marker='o', linestyle='--', markersize=1, color=colors[color_ctr], markeredgecolor=colors[color_ctr])
            color_ctr += 1
        plt.xlabel('time (ms)')
        plt.ylabel('Flow Rate (Mbps)')

        color_ctr = 0
        plt.subplot(615)
        sorted_linkIDs = sorted(self.link_packet_lost.keys())
        for linkID in sorted_linkIDs[:num_plotted_links]:
            link_dict = self.link_packet_lost[linkID]
            sorted_time = sorted(link_dict)
            l_pkt_lost = []
            for time in sorted_time:
                l_pkt_lost.append(link_dict[time])
            plt.plot(sorted_time, l_pkt_lost, label=linkID, marker='o', linestyle='--', markersize=1, color=colors[color_ctr], markeredgecolor=colors[color_ctr])
            color_ctr += 1
        plt.legend(bbox_to_anchor=(1,1))
        plt.xlabel('time (ms)')
        plt.ylabel('Packets Dropped')

        color_ctr = 0
        plt.subplot(616)        # link rate plot
        sorted_flowIDs = sorted(self.flow_window_size.keys())
        for flowID in sorted_flowIDs:
            if constants.debug:
                print("WINDOW SIZE FLOW ID:")
                print(flowID + " " + colors[color_ctr])
            #if list(self.link_flow_rate.keys()).index(linkID) is not 1:
            # Get time out of [time, rate] pairs
            time = [elt[0] for elt in self.flow_window_size[flowID]]
            # Get rate out of [time, rate] pairs
            flow_ws = [elt[1] for elt in self.flow_window_size[flowID]]
            plt.plot(time, flow_ws, label=flowID, marker='o', linestyle='--', markersize=1, color=colors[color_ctr], markeredgecolor=colors[color_ctr])
            color_ctr += 1
        plt.legend(bbox_to_anchor=(1,1))
        plt.xlabel('time (ms)')
        plt.ylabel('Window Size (pkts)')
        # ALSO FIX UNITS

        plt.show()
