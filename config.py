import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    MIN_RELEVANCE_THRESHOLD: float = float(os.getenv("MIN_RELEVANCE_THRESHOLD", "0.1"))

    # Database path
    DB_PATH: str = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "evaluation_logs.db"))

    # Comprehensive dictionaries of domain-specific terms (stored as lowercase sets for fast matching)
    DOMAIN_KEYWORDS: dict[str, set[str]] = {
        "dsa": {
            "array", "vector", "list", "linked list", "singly", "doubly", "stack", "queue", "deque", 
            "priority queue", "heap", "min-heap", "max-heap", "tree", "binary tree", "binary search tree", 
            "bst", "avl", "red-black", "b-tree", "trie", "graph", "hash", "hash table", "hash map", 
            "collision", "chaining", "open addressing", "segment tree", "fenwick", "disjoint set", "union find",
            "sorting", "quicksort", "mergesort", "heapsort", "bubble sort", "insertion sort", "selection sort", 
            "radix sort", "counting sort", "binary search", "linear search", "bfs", "breadth-first search", 
            "dfs", "depth-first search", "dijkstra", "bellman-ford", "floyd-warshall", "kruskal", "prim", 
            "topological sort", "dynamic programming", "dp", "backtracking", "recursion", "recursive", 
            "greedy", "divide and conquer", "sliding window", "two pointers", "big o", "time complexity", 
            "space complexity", "asymptotic", "linear", "quadratic", "logarithmic", "exponential", "memoization"
        },
        "dbms": {
            "database", "dbms", "rdbms", "nosql", "schema", "table", "relation", "tuple", "row", "record", 
            "column", "attribute", "field", "primary key", "foreign key", "candidate key", "super key", 
            "composite key", "unique constraint", "index", "indexing", "b-tree", "hash index", "clustered index", 
            "non-clustered index", "sql", "query", "select", "insert", "update", "delete", "join", "inner join", 
            "left join", "right join", "outer join", "cross join", "self join", "group by", "order by", 
            "having", "aggregate", "sum", "count", "avg", "min", "max", "view", "stored procedure", "trigger", 
            "transaction", "acid", "atomicity", "consistency", "isolation", "durability", "concurrency", 
            "concurrency control", "locking", "shared lock", "exclusive lock", "two-phase locking", "2pl", 
            "deadlock", "write-ahead logging", "wal", "recovery", "normalization", "1nf", "2nf", "3nf", "bcnf", 
            "4nf", "5nf", "denormalization", "sharding", "replication", "cap theorem", "mongodb", "redis", "cassandra"
        },
        "os": {
            "process", "thread", "multithreading", "multiprocessing", "pcb", "process control block", 
            "context switch", "scheduling", "scheduler", "fcfs", "sjf", "round robin", "priority scheduling", 
            "multi-level queue", "srtf", "thread pool", "concurrency", "synchronization", "race condition", 
            "critical section", "mutual exclusion", "mutex", "semaphore", "counting semaphore", 
            "binary semaphore", "deadlock", "starvation", "livelock", "bankers algorithm", "dining philosophers", 
            "producer consumer", "reader writer", "memory", "physical memory", "virtual memory", "paging", 
            "page table", "tlb", "translation lookaside buffer", "page fault", "demand paging", "page replacement", 
            "fifo", "lru", "optimal", "mru", "clock replacement", "segmentation", "fragmentation", 
            "internal fragmentation", "external fragmentation", "compaction", "kernel", "microkernel", 
            "monolithic", "system call", "user mode", "kernel mode", "privileged", "file system", "inode", 
            "metadata", "directory", "disk scheduling", "sstf", "scan", "c-scan", "look", "c-look", 
            "bootloader", "interrupt", "isr", "interrupt service routine", "cache", "spooling", "buffering"
        }
    }

    def __init__(self):
        # Expand multi-word keywords to also match individual words (e.g. "primary key" -> "primary", "key")
        expanded = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            words = set()
            for kw in keywords:
                words.add(kw)
                if " " in kw:
                    words.update(kw.split())
            expanded[domain] = words
        self.DOMAIN_KEYWORDS = expanded

settings = Settings()
