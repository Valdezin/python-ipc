import multiprocessing
import multiprocessing.shared_memory
import time
from responses import responses

def chatbot(queue, shared_mem_name, semaphore):
    shm = multiprocessing.shared_memory.SharedMemory(name=shared_mem_name)

    while True:
        user_input = queue.get()
        print(f"\n                                                        You: {user_input}\n")

        if user_input.lower() == "exit":
            break

        response = responses.get(user_input.lower(), responses["default"])

        semaphore.acquire()
        shm.buf[:len(response)] = response.encode('utf-8') 
        semaphore.release()

        queue.put(response)
        time.sleep(1)
    
    shm.close()

if __name__ == "__main__":
    print("Welcome to Chatbot! Type your message below or type 'exit' to quit.")
    
    queue = multiprocessing.Queue()
    shm = multiprocessing.shared_memory.SharedMemory(create=True, size=256)
    semaphore = multiprocessing.Semaphore(1)
    
    chatbot_process = multiprocessing.Process(target=chatbot, args=(queue, shm.name, semaphore))
    chatbot_process.start()
    
    while True:
        user_input = input()
        queue.put(user_input)
        
        if user_input.lower() == "exit":
            break
        
        response = queue.get()
        print(f"Chatbot: {response}")
        
        semaphore.acquire()
        stored_response = bytes(shm.buf[:len(response)]).decode('utf-8').strip('\x00')
        semaphore.release()
        
        print(f"(Shared Memory) Chatbot stored: {stored_response}\n")
    
    chatbot_process.terminate()
    chatbot_process.join()
    shm.close()
    shm.unlink()
