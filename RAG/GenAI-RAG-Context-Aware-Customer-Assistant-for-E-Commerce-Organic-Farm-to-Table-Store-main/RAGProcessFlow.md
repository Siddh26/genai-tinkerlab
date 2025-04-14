```mermaid
graph TD
    A[User] -->|Sends query| B[Flask API]
    B -->|Passes query| C[RAGChatbot]
    C -->|Uses| D[LangChain]
    D -->|Embeds query| E[OpenAI Embeddings]
    E -->|Vector representation| F[ChromaDB]
    F -->|Retrieves similar docs| G[LangChain RetrievalQA]
    G -->|Combines query & docs| H[PromptTemplate]
    H -->|Structured prompt| I[ChatGPT Model]
    I -->|Generates response| J[LangChain]
    J -->|Passes response| C
    C -->|Returns response| B
    B -->|Delivers response| A

    K[Desi Bazar Agro Data] -->|Preprocessing| L[populate_db.py]
    L -->|Embeds documents| M[OpenAI Embeddings]
    M -->|Vector representations| N[ChromaDB]

    O[config.json] -->|Configures| C
    P[.env] -->|Provides API Key| C

    subgraph "RAGChatbot Class"
        C
        D
        G
        J
    end

    subgraph "Data Storage"
        F
        N
    end

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style I fill:#fcc,stroke:#333,stroke-width:2px
    style F fill:#cfc,stroke:#333,stroke-width:2px
    style N fill:#cfc,stroke:#333,stroke-width:2px
    style K fill:#ccf,stroke:#333,stroke-width:2px
    style O fill:#ffc,stroke:#333,stroke-width:2px
    style P fill:#ffc,stroke:#333,stroke-width:2px
    ```