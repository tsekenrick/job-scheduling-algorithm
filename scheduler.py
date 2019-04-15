# -*- coding: utf-8 -*-
"""

@author: Kenrick Tse
"""
import sys
import copy
class Process:
    
    def __init__ (self, data):
        self.start_time = data[0]
        self.max_cpu_burst = data[1]
        self.req_cpu = data[2] #total cpu cycles needed
        self.remaining_cpu = data[2] #cpu cycles left until termination
        self.io_multi = data[3]
        
        self.state = 'unstarted'
        self.state_dur = 0 #used to track how long a process is running or blocked
        self.state_dur_max = 0 #starting value of state_dur
        self.state_hist = [] #state of process across all cycles
        
        self.time_waiting = 0 #how many cycles a process has been ready for without running
        
        self.finish_time = 0
        self.io_time = 0
        
        #for RR
        self.preemptable = False
        self.preempt_counter = 2
        self.total_waiting = 0
        #for HPRN
        self.pen_ratio = 0
        self.total_run = 0
        
    def decr_state(self, cycle, rand_nums):
        #if-else block for decrementing state, doesn't check for state changing
        
        if(self.state == 'unstarted'):
            if cycle == self.start_time:
                self.state = 'ready'
        
        if(self.state == 'blocked'):
            self.state_dur -= 1
            self.io_time += 1
            if self.state_dur == 0:
                self.state = 'ready'
                
        if(self.state == 'running'):
            self.remaining_cpu -= 1
            self.state_dur -= 1
            self.total_run += 1
            if self.preemptable:
                self.preempt_counter -= 1
            
            
            #possible state changes
            if self.remaining_cpu == 0:
                self.state = 'terminated'
                self.finish_time = cycle
            elif self.state_dur == 0:
                self.state = 'blocked'
                self.preempt_counter = 2
                self.state_dur = self.state_dur_max * self.io_multi
            elif self.preempt_counter == 0:
                self.state = 'ready'
                self.preempt_counter = 2
            
            
        
        if(self.state == 'ready'):
            self.time_waiting += 1
            self.total_waiting += 1
            
    
    def state_to_hist(self, cycle):
        
        if self.state == 'unstarted':
            self.state_hist.append('unstarted  0')

        if self.state == 'blocked':
            self.state_hist.append(f'blocked{self.state_dur:>3}')
            
        if self.state == 'running' and not self.preemptable:
            self.state_hist.append(f'running{self.state_dur:>3}')
            
        if self.state == 'running' and self.preemptable:
            self.state_hist.append(f'running{self.preempt_counter:>3}')
            
        if self.state == 'ready':
            self.state_hist.append('ready  0')
            
        if self.state == 'terminated':
            self.state_hist.append('terminated  0')
            
    def flip_preemptable(self):
        self.preemptable = not self.preemptable
        
    def calc_pen_ratio(self, cycle):
        lifetime = cycle - self.start_time
        runtime = max(1, self.total_run)
        self.pen_ratio = lifetime/runtime
        
        return self.pen_ratio
    
    def process_data(self, process_num):
        ret_str = f'Process {process_num}:\n'
        ret_str += f'\t(A,C,B,M) = {str(self)}\n'
        ret_str += f'\tFinishing time: {self.finish_time}\n'
        ret_str += f'\tTurnaround time: {self.finish_time - self.start_time}\n'
        ret_str += f'\tI/O time: {self.io_time}\n'
        ret_str += f'\tWaiting time: {self.total_waiting}\n\n'
        return ret_str
            
    def __str__(self):
        return f'({self.start_time} {self.max_cpu_burst} {self.req_cpu} {self.io_multi})'
    
    def __repr__(self):
        return str(self)
    

def fcfs(count, data, rand_nums):

    cycle = 0
    rand_idx = 0 #for determining which rand num to use
    
    #loop runs once per update cycle - decrements all process states and makes
    #necessary state changes
    while not all_processes_terminated(data):
        for process in data:
            process.state_to_hist(cycle)
            process.decr_state(cycle, rand_nums)
            
        # if no process running, select a new process to run based on fcfs
        #this may need to be moved above decr_state or rearranged - testing needed
        if not(process_running(data) and num_processes_ready(data) > 0):
            max_wait = 0 #tracks the process that has waited longest
            process_to_run = None
            #find process that has been ready for longest
            for i, process in enumerate(data):
                if process.state == 'ready':
                    if process.time_waiting > max_wait:
                        process_to_run = i
                        max_wait = process.time_waiting
                        
                    # apply lab 2 tiebreak
                    elif process.time_waiting == max_wait and max_wait != 0:
                        candidate1 = i
                        candidate2 = process_to_run
                        if data[candidate1].start_time < data[candidate2].start_time:
                            process_to_run = candidate1
                        elif data[candidate1].start_time == data[candidate2].start_time:
                            process_to_run = candidate1 if candidate1 < candidate2 else candidate2
                            
            # run the elected process
            if(process_to_run != None):    
                data[process_to_run].time_waiting = 0
                data[process_to_run].state = 'running'
                data[process_to_run].total_waiting -= 1 # account for off by one error
                
                # get random burst based on random numbers file
                data[process_to_run].state_dur = randOS(data[process_to_run].max_cpu_burst, rand_nums, rand_idx)
                
                if data[process_to_run].state_dur > data[process_to_run].remaining_cpu:
                    data[process_to_run].state_dur = data[process_to_run].remaining_cpu   
                    
                data[process_to_run].state_dur_max = data[process_to_run].state_dur
                rand_idx += 1

        cycle+=1
    
    return data

def rr(count, data, rand_nums):
    for i, process in enumerate(data):
        process.flip_preemptable()
        
    cycle = 0
    rand_idx = 0

    while not all_processes_terminated(data):
        for process in data:
            process.state_to_hist(cycle)
            process.decr_state(cycle, rand_nums)
            
        # if no process running, select a new process to run based on fcfs
        #this may need to be moved above decr_state or rearranged - testing needed
        if not(process_running(data) and num_processes_ready(data) > 0):
            max_wait = 0 #tracks the process that has waited longest
            process_to_run = None
            
            #find process that has been ready for longest
            for i, process in enumerate(data):
                if process.state == 'ready':
                    if process.time_waiting > max_wait:
                        process_to_run = i
                        max_wait = process.time_waiting
                        
                    # apply lab 2 tiebreak
                    elif process.time_waiting == max_wait and max_wait != 0:
                        candidate1 = i
                        candidate2 = process_to_run
                        if data[candidate1].start_time < data[candidate2].start_time:
                            process_to_run = candidate1
                        elif data[candidate1].start_time == data[candidate2].start_time:
                            process_to_run = candidate1 if candidate1 < candidate2 else candidate2
                            
            # run the elected process
            if(process_to_run != None):    
                data[process_to_run].time_waiting = 0
                data[process_to_run].state = 'running'
                data[process_to_run].total_waiting -= 1 # account for off by one error
                
                # get random burst based on random numbers file
                if data[process_to_run].state_dur == 0:
                    data[process_to_run].state_dur = randOS(data[process_to_run].max_cpu_burst, rand_nums, rand_idx)
                
                    if data[process_to_run].state_dur > data[process_to_run].remaining_cpu:
                        data[process_to_run].state_dur = data[process_to_run].remaining_cpu   
                    
                    data[process_to_run].state_dur_max = data[process_to_run].state_dur
                    rand_idx += 1
        cycle+=1
    
    #may be extranneous
    for i, process in enumerate(data):
        process.flip_preemptable()
        
    return data

def lcfs(count, data, rand_nums):
    
    cycle = 0
    rand_idx = 0 #for determining which rand num to use
    
    #loop runs once per update cycle - decrements all process states and makes
    #necessary state changes
    while not all_processes_terminated(data):
        for process in data:
            process.state_to_hist(cycle)
            process.decr_state(cycle, rand_nums)
            
        # if no process running, select a new process to run based on fcfs
        #this may need to be moved above decr_state or rearranged - testing needed
        if not(process_running(data) and num_processes_ready(data) > 0):
            min_wait = float('inf') #tracks the process that has waited longest
            process_to_run = None
            #find process that has been ready for longest
            for i, process in enumerate(data):
                if process.state == 'ready':
                    if process.time_waiting < min_wait:
                        process_to_run = i
                        min_wait = process.time_waiting
                        
                    # apply lab 2 tiebreak
                    elif process.time_waiting == min_wait and min_wait != 0:
                        candidate1 = i
                        candidate2 = process_to_run
                        if data[candidate1].start_time < data[candidate2].start_time:
                            process_to_run = candidate1
                        elif data[candidate1].start_time == data[candidate2].start_time:
                            process_to_run = candidate1 if candidate1 < candidate2 else candidate2
                            
            # run the elected process
            if(process_to_run != None):    
                data[process_to_run].time_waiting = 0
                data[process_to_run].state = 'running'
                data[process_to_run].total_waiting -= 1 # account for off by one error
                
                # get random burst based on random numbers file
                data[process_to_run].state_dur = randOS(data[process_to_run].max_cpu_burst, rand_nums, rand_idx)
                
                if data[process_to_run].state_dur > data[process_to_run].remaining_cpu:
                    data[process_to_run].state_dur = data[process_to_run].remaining_cpu   
                    
                data[process_to_run].state_dur_max = data[process_to_run].state_dur
                rand_idx += 1

        cycle+=1
    
    return data

def hprn(count, data, rand_nums):

    cycle = 0
    rand_idx = 0 #for determining which rand num to use
    
    #loop runs once per update cycle - decrements all process states and makes
    #necessary state changes
    while not all_processes_terminated(data):
        for process in data:
            process.state_to_hist(cycle)
            process.decr_state(cycle, rand_nums)
            
        # if no process running, select a new process to run based on fcfs
        #this may need to be moved above decr_state or rearranged - testing needed
        if not(process_running(data) and num_processes_ready(data) > 0):
            max_pr = -1 #tracks the process of highest penalty ratio
            process_to_run = None
            #find process that has highest PR
            for i, process in enumerate(data):
                if process.state == 'ready':
                    if process.calc_pen_ratio(cycle) > max_pr:
                        process_to_run = i
                        max_pr = process.calc_pen_ratio(cycle)
                        
                    # apply lab 2 tiebreak
                    elif process.calc_pen_ratio(cycle) == max_pr and max_pr != 0:
                        candidate1 = i
                        candidate2 = process_to_run
                        if data[candidate1].calc_pen_ratio(cycle) < data[candidate2].calc_pen_ratio(cycle):
                            process_to_run = candidate1
                        elif data[candidate1].calc_pen_ratio(cycle) == data[candidate2].calc_pen_ratio(cycle):
                            process_to_run = candidate1 if candidate1 < candidate2 else candidate2
                            
            # run the elected process
            if(process_to_run != None):    
                data[process_to_run].time_waiting = 0
                data[process_to_run].state = 'running'
                data[process_to_run].total_waiting -= 1 # account for off by one error
                
                # get random burst based on random numbers file
                data[process_to_run].state_dur = randOS(data[process_to_run].max_cpu_burst, rand_nums, rand_idx)
                
                if data[process_to_run].state_dur > data[process_to_run].remaining_cpu:
                    data[process_to_run].state_dur = data[process_to_run].remaining_cpu   
                    
                data[process_to_run].state_dur_max = data[process_to_run].state_dur
                rand_idx += 1

        cycle+=1
    
    return data

def all_processes_terminated(data):
    for process in data:
        if process.state != 'terminated':
            return False
        
    return True

def process_running(data):
    for process in data:
        if process.state == 'running':
            return True
    
    return False

def num_processes_ready(data):
    ready_count = 0
    for process in data:
        if process.state == 'ready':
            ready_count += 1
    
    return ready_count

def randOS(U, num_list, rand_idx):
    return 1 + (num_list[rand_idx] % U)

def summary_data(data):
    ret_str = 'Summary Data:\n'
    ret_str += f'\tFinishing time: {len(data[0].state_hist) - 1}\n'
    
    utilized = 0
    for cycle in range(len(data[0].state_hist)):
        for process in data:
            if 'running' in process.state_hist[cycle]: utilized += 1
            
    ret_str += f'\tCPU Utilization: {utilized/(len(data[0].state_hist) - 1):.6f}\n'
    
    io_utilized = 0
    counted_cycle = False
    for cycle in range(len(data[0].state_hist)):
        counted_cycle = False
        for process in data:
            if 'blocked' in process.state_hist[cycle]: 
                if not counted_cycle: io_utilized += 1
                counted_cycle = True
                
    ret_str += f'\tI/O Utilization: {io_utilized/(len(data[0].state_hist) - 1):.6f}\n'
    ret_str += f'\tThroughput: {(len(data)/len(data[0].state_hist))*100:.6f}\n'
    
    turnaround_sum = 0
    for process in data:
        turnaround_sum += process.finish_time - process.start_time
    turnaround_avg = turnaround_sum/len(data)
    
    ret_str += f'\tAverage turnaround time: {turnaround_avg:.6f}\n'
    
    wait_sum = 0
    for process in data:
        wait_sum += process.total_waiting
    wait_avg = wait_sum/len(data)
    
    ret_str += f'\tAverage wait time: {wait_avg:.6f}\n'
    
    return ret_str
if __name__ == '__main__':

    with open(sys.argv[len(sys.argv) - 1], 'r') as input_file:
        raw = input_file.read()
    
    with open('random-numbers.txt', 'r') as rand_file:
        rand_nums = rand_file.readlines()
    
    #clean up random number list
    for i, num in enumerate(rand_nums):
        num = int(num.strip())
        rand_nums[i] = num
    
    #clean up input data
    process_count = int(raw[0])
    raw = raw[1:] #grab then remove process count
    
    header_filter = filter(lambda x: x in '0123456789() ', raw)
    header = str(process_count) #for output printing later
    for char in header_filter:
        header += char
    header = header.strip()
        
    #filter function removes everything but numbers and spaces
    filtered = filter(lambda x: x in '0123456789 ', raw)
    clean_raw = ''
    for char in filtered:
        clean_raw += char 
    
    #remove leading and trailing spaces with strip
    clean_raw = clean_raw.strip()
    
    #create new list data and convert strings to ints
    data = clean_raw.split(' ')
    for i, item in enumerate(data):
        data[i] = int(data[i])
        
    processes = []
    for i in range(process_count):
        processes.append(Process(data[i * 4 : i * 4 + 4]))
    
    #run the policies
    fcfs_res = fcfs(process_count, copy.deepcopy(processes), copy.deepcopy(rand_nums))
    rr_res = rr(process_count, copy.deepcopy(processes), copy.deepcopy(rand_nums))
    lcfs_res= lcfs(process_count, copy.deepcopy(processes), copy.deepcopy(rand_nums))
    hprn_res = hprn(process_count, copy.deepcopy(processes), copy.deepcopy(rand_nums))
    res_list = [fcfs_res, rr_res, lcfs_res, hprn_res]
    policy_names = ["First Come First Served", "Round Robin", "Last Come First Served", "Highest Penalty Ratio Next"]
    
    for results in res_list:
        results.sort(key = lambda process: process.start_time)  
    sort_header = f'The (sorted) input is:  {process_count} '
    for process in res_list[0]:
        sort_header += f'{process} '
    sort_header += '\n'
    
    #print output, either detailed or basic depending on cmd arg
    if(sys.argv[1] == '--verbose'):
        for j, results in enumerate(res_list):
            print(f'The original input was: {header}')
            print(sort_header)
            
            # put detailed things here       
            print('This detailed printout gives the state and remaining burst for each process\n')
            this_cycle = ''
            for i in range(len(results[0].state_hist)):
                this_cycle = f'Before cycle {i:>5}:'
                for process in results:
                    this_cycle += f'{process.state_hist[i]:>15}'
                this_cycle += '.'
                print(this_cycle)
            print(f'\nThe scheduling algorithm used was {policy_names[j]}\n')
            for i, process in enumerate(results): 
                print(process.process_data(i))
                
            print(summary_data(results))
        
    else:
        for j, results in enumerate(res_list):
            print(f'The original input was: {header}')
            print(sort_header)
            print(f'The scheduling algorithm used was {policy_names[j]}\n')
            for i, process in enumerate(results):
                print(process.process_data(i))
            
            print(summary_data(results))


        
   