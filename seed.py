import os
import random
from datetime import datetime, timedelta
import sqlite3

# Import database path setting or fallback
from app.config import settings
from app.database import init_db

# Mock Data Templates
QUESTIONS_ANSWERS = [
    # DSA
    {
        "domain": "dsa",
        "question": "What is the time complexity of quicksort in the worst case and how can we avoid it?",
        "answer": "The worst-case time complexity of quicksort is O(n^2). This happens when the pivot chosen is always the smallest or largest element, e.g., when the array is already sorted. We can avoid this by choosing a random pivot or using the median-of-three pivot selection technique.",
        "score": 9.0,
        "feedback": "Perfect explanation of the worst-case complexity and correct suggestion of random or median-of-three pivot selection to mitigate it.",
        "confidence": 0.95,
        "method": "llm",
        "provider": "gemini"
    },
    {
        "domain": "dsa",
        "question": "Explain the difference between a stack and a queue.",
        "answer": "A stack is a Last-In-First-Out (LIFO) data structure, whereas a queue is a First-In-First-Out (FIFO) data structure. You push and pop from a stack, and enqueue and dequeue from a queue.",
        "score": 8.0,
        "feedback": "Clear and accurate definitions of LIFO and FIFO behaviors along with corresponding operations.",
        "confidence": 0.90,
        "method": "llm",
        "provider": "openai"
    },
    {
        "domain": "dsa",
        "question": "How does a hash table handle collisions?",
        "answer": "Collisions happen when different keys hash to the same index. They are handled using chaining (linked lists at each bucket) or open addressing (linear probing, quadratic probing, or double hashing to find another empty bucket).",
        "score": 8.5,
        "feedback": "Correctly identifies chaining and open addressing as the two main techniques for collision resolution.",
        "confidence": 0.92,
        "method": "llm",
        "provider": "gemini"
    },
    {
        "domain": "dsa",
        "question": "What is a binary search tree?",
        "answer": "It is a tree structure where each node has at most two children, and the left child is smaller while the right is larger.",
        "score": 6.5,
        "feedback": "Conceptually correct, but lacks formal details such as node values relation and recursive definition.",
        "confidence": 0.75,
        "method": "llm",
        "provider": "openai"
    },
    {
        "domain": "dsa",
        "question": "Describe Dijkstra's algorithm.",
        "answer": "It finds the shortest path in a graph. It uses a priority queue.",
        "score": 4.5,
        "feedback": "Extremely brief. Fails to describe how relaxation works or that it only applies to non-negative edge weights.",
        "confidence": 0.60,
        "method": "llm",
        "provider": "gemini"
    },
    {
        "domain": "dsa",
        "question": "What is dynamic programming?",
        "answer": "We cook food by dividing it into recipes.",
        "score": 0.0,
        "feedback": "The answer is completely irrelevant to the question or the domain of DSA.",
        "confidence": 1.0,
        "method": "rule_based",
        "provider": None
    },

    # DBMS
    {
        "domain": "dbms",
        "question": "What are ACID properties in database transactions?",
        "answer": "ACID stands for Atomicity (all or nothing), Consistency (preserves database rules), Isolation (transactions run independently without interfering), and Durability (saved permanently even after crash).",
        "score": 9.5,
        "feedback": "Excellent definition of each component of the ACID properties. Highly accurate.",
        "confidence": 0.98,
        "method": "llm",
        "provider": "gemini"
    },
    {
        "domain": "dbms",
        "question": "Explain the difference between clustered and non-clustered indexes.",
        "answer": "A clustered index defines the physical order of rows in the table (only one per table). A non-clustered index has a separate structure containing keys and pointers to the actual data rows (multiple allowed).",
        "score": 8.8,
        "feedback": "Correct explanation of physical sorting vs pointer-based indexing.",
        "confidence": 0.92,
        "method": "llm",
        "provider": "openai"
    },
    {
        "domain": "dbms",
        "question": "What is normalization and why do we use it?",
        "answer": "Normalization is organizing data to reduce redundancy and improve data integrity. We use normal forms like 1NF, 2NF, and 3NF by splitting tables and using foreign keys.",
        "score": 8.2,
        "feedback": "Good summary of redundancy reduction and references to 1NF, 2NF, and 3NF standard forms.",
        "confidence": 0.88,
        "method": "llm",
        "provider": "gemini"
    },
    {
        "domain": "dbms",
        "question": "What is a primary key?",
        "answer": "A column that uniquely identifies a row in a table. It cannot contain null values.",
        "score": 7.8,
        "feedback": "Correct definition highlighting uniqueness and non-nullability constraints.",
        "confidence": 0.45,
        "method": "rule_based",
        "provider": None
    },
    {
        "domain": "dbms",
        "question": "What is a database join?",
        "answer": "A way to combine rows from two or more tables based on a related column between them, like inner join, left join, and outer join.",
        "score": 8.0,
        "feedback": "Correctly defines joins and lists common join types.",
        "confidence": 0.85,
        "method": "llm",
        "provider": "openai"
    },

    # OS
    {
        "domain": "os",
        "question": "What is the difference between a process and a thread?",
        "answer": "A process is an executing instance of a program with its own memory space. A thread is a path of execution within a process, sharing memory and resources with other threads in the same process.",
        "score": 9.2,
        "feedback": "Superb answer detailing resource ownership differences and execution context sharing.",
        "confidence": 0.95,
        "method": "llm",
        "provider": "gemini"
    },
    {
        "domain": "os",
        "question": "How does virtual memory work using paging?",
        "answer": "Virtual memory splits logical memory into pages and physical memory into frames. The Operating System uses a page table and Translation Lookaside Buffer (TLB) to map virtual addresses to physical ones, loading pages to disk when physical RAM is full.",
        "score": 9.0,
        "feedback": "Solid coverage of pages/frames, page tables, TLB, and paging out to disk.",
        "confidence": 0.94,
        "method": "llm",
        "provider": "openai"
    },
    {
        "domain": "os",
        "question": "What is a deadlock and what are its four necessary conditions?",
        "answer": "A deadlock is when processes are blocked waiting for resources held by each other. The conditions are Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait.",
        "score": 9.5,
        "feedback": "Perfect response. Accurately names and defines all four Coffman deadlock conditions.",
        "confidence": 0.97,
        "method": "llm",
        "provider": "gemini"
    },
    {
        "domain": "os",
        "question": "What is a semaphore?",
        "answer": "A variable or abstract data type used to control access to a common resource by multiple processes in a concurrent system.",
        "score": 8.0,
        "feedback": "Good definition of semaphores for resource synchronization.",
        "confidence": 0.85,
        "method": "llm",
        "provider": "openai"
    },
    {
        "domain": "os",
        "question": "Explain Thrashing in Operating Systems.",
        "answer": "Thrashing happens when the OS spends more time swapping pages in and out of disk than executing instructions. It happens when physical memory is too small for the working set.",
        "score": 8.7,
        "feedback": "Clear explanation of CPU under-utilization due to excessive page faults.",
        "confidence": 0.90,
        "method": "llm",
        "provider": "gemini"
    }
]

def seed_database(num_records: int = 50):
    """Seed the database with mock evaluation data spread over the last 30 days."""
    init_db()
    
    conn = sqlite3.connect(settings.DB_PATH)
    
    # Check if we already have records
    count = conn.execute("SELECT COUNT(*) FROM evaluation_logs").fetchone()[0]
    if count >= num_records:
        print(f"Database already has {count} records. Skipping seeding.")
        conn.close()
        return

    print(f"Seeding database with {num_records} mock evaluation logs...")
    
    now = datetime.utcnow()
    
    for i in range(num_records):
        # Pick a random template
        tmpl = random.choice(QUESTIONS_ANSWERS)
        
        # Calculate random timestamp within the last 30 days
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        mins_ago = random.randint(0, 59)
        timestamp = (now - timedelta(days=days_ago, hours=hours_ago, minutes=mins_ago)).isoformat() + "Z"
        
        # Slightly jitter the score and confidence for variance
        score = tmpl["score"]
        if score > 0.0:
            score = max(1.0, min(10.0, score + round(random.uniform(-1.5, 1.5), 1)))
        
        confidence = tmpl["confidence"]
        if confidence < 1.0:
            confidence = max(0.3, min(1.0, confidence + round(random.uniform(-0.1, 0.1), 2)))
            
        conn.execute(
            """
            INSERT INTO evaluation_logs 
                (timestamp, question, answer, domain, score, feedback, confidence, evaluation_method, llm_provider)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                tmpl["question"],
                tmpl["answer"],
                tmpl["domain"],
                score,
                tmpl["feedback"],
                confidence,
                tmpl["method"],
                tmpl["provider"]
            )
        )
        
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM evaluation_logs").fetchone()[0]
    print(f"Seeding complete. Total records in database: {total}")
    conn.close()

if __name__ == "__main__":
    seed_database()
