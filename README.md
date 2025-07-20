# Meeting-ActionAgent

## Project Title & Description

This project aims to provide an intelligent agent capable of actively participating in meetings, understanding the discussed topics, and generating actionable items. This project structure suggests a focus on real-time voice processing from 2 separate audio streams of a microphone and system audio from browser and then taking action on platforms lik Google Calendar, Slack, Brave Browser and Github.

## Key Features & Benefits

*   **Real-time Voice Processing:** The `app` directory suggests real-time audio capture and processing capabilities.
*   **Action Item Extraction:** The agent is intended to identify and extract action items from meeting discussions.
*   **Web-based Interface:** The `app` directory includes a web interface for interacting with the agent.

## Prerequisites & Dependencies

Before you begin, ensure you have the following installed:

*   **Python 3.10+**
*   **Node.js and npm (Node Package Manager)** (for the web app)
*   **uv (Ultraviolet package manager)**  - used for managing python packages

## Installation & Setup Instructions

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Aseer-Ahmad/Meeting-ActionAgent.git
    cd Meeting-ActionAgent
    ```

2.  **Set up the Python environment:**

    Install python dependencies. It is highly suggested to use a virtual environment.

    ```bash
    # Create and activate a virtual environment (optional but recommended)
    python3 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    # .venv\Scripts\activate  # On Windows

    uv pip install -r requirements.txt
    ```
4.  **API keys:**

    Set the following API keys in your .env file. 
    ACI_API_KEY refers to Aci.dev (https://www.aci.dev/) for MCP and tool integration.

    ```
    OPENAI_API_KEY, ACI_API_KEY
    ```

4.  **Run the application server:**

    ```bash
    cd app
    uv run python server.py
    ```

    This will start the FastAPI server, likely on `http://localhost:8000`.

5.  **Access the web interface:**

    Open your web browser and navigate to the address provided by the server (usually `http://localhost:8000`).

## Usage Examples & API Documentation (if applicable)

### Web Application

1.  **Connect:** Click the "Connect" button on the web interface to establish a audio streaming from a browser window and establish a session.
2.  **Speak:** The application should automatically start capturing audio. Speak naturally into your microphone.
3.  **Observe:** Monitor the agent's as events, tools called and agent hand-offs.

## Configuration Options

The `app/server.py` file likely contains configuration options for the FastAPI server. Inspect this file for customizable settings such as:

*   **Port number:** The port on which the server listens for connections.
*   **Agent parameters:** Parameters that control the behavior of the action extraction agent.
*   **Audio processing settings:** Settings related to audio capture and processing.

## Contributing Guidelines

Contributions are welcome! To contribute to this project, follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Implement your changes and write appropriate tests.
4.  Submit a pull request with a clear description of your changes.

## License Information

License information is not explicitly specified in the provided repository information.  It is assumed to be proprietary or under development. Adding a License (e.g., MIT, Apache 2.0) is highly recommended.

## Acknowledgments (if relevant)

If the project utilizes any third-party libraries, datasets, or resources, please acknowledge them here.
