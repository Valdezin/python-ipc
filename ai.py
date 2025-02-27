import multiprocessing
import multiprocessing.shared_memory
import time
import sys
from openai import OpenAI
from apikey import API_KEY

API_KEY = API_KEY.get("apiKey")

def validate_api():
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=API_KEY,
        )

        client.chat.completions.create(
            model="qwen/qwen2.5-vl-72b-instruct:free",
            messages=[{"role": "user", "content": "Hello"}]
        )
        return client

    except Exception as e:
        print(f"API Key validation failed: {e}")
        return None


def chatbot(queue, shared_mem_name, semaphore, api_key):
    client = validate_api()
    if client is None:
        queue.put("API connection failed. Please check your API key.")
        return

    shm = multiprocessing.shared_memory.SharedMemory(name=shared_mem_name)

    while True:
        user_input = queue.get()
        print(f"\n                                                        You: {user_input}\n")

        if user_input.lower() == "exit":
            break

        completion = client.chat.completions.create(
            model="qwen/qwen2.5-vl-72b-instruct:free",
            messages=[{"role": "user", "content": user_input}]
        )
        response = completion.choices[0].message.content.strip()

        max_size = shm.size  
        encoded_response = response.encode('utf-8')[:max_size]

        semaphore.acquire()
        shm.buf[:len(encoded_response)] = encoded_response  
        shm.buf[len(encoded_response):] = b'\x00' * (max_size - len(encoded_response))  
        semaphore.release()

        queue.put(response)
        time.sleep(1)

    shm.close()


def display_typing_effect(text):
    words = text.split()
    for word in words:
        sys.stdout.write(word + " ")
        sys.stdout.flush()
        time.sleep(0.15)
    print("\n")


if __name__ == "__main__":
    print("Validating API key...")

    client = validate_api()
    if client is None:
        print("Exiting program due to invalid API key.")
        exit()

    print("API key validated. Welcome to Chatbot! Type your message below or type 'exit' to quit.")

    queue = multiprocessing.Queue()
    shm = multiprocessing.shared_memory.SharedMemory(create=True, size=1024)
    semaphore = multiprocessing.Semaphore(1)

    chatbot_process = multiprocessing.Process(target=chatbot, args=(queue, shm.name, semaphore, API_KEY))
    chatbot_process.start()

    while True:
        user_input = input()
        queue.put(user_input)

        if user_input.lower() == "exit":
            break

        response = queue.get()

        print("Chatbot: ", end="", flush=True)
        display_typing_effect(response)

        semaphore.acquire()
        stored_response = bytes(shm.buf[:]).decode('utf-8').rstrip('\x00')
        semaphore.release()

        print(f"(Shared Memory) Chatbot stored: {stored_response}\n")

    chatbot_process.terminate()
    chatbot_process.join()
    shm.close()
    shm.unlink()
