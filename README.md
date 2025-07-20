# Meeting-ActionAgent

## Project Title & Description

This project aims to provide an intelligent agent capable of actively participating in meetings, understanding the discussed topics, and generating actionable items. While the repository lacks a comprehensive initial description, the project structure suggests a focus on real-time voice processing and action item extraction.

## Key Features & Benefits

*   **Real-time Voice Processing:** The `app` directory suggests real-time audio capture and processing capabilities.
*   **Action Item Extraction:** The agent is intended to identify and extract action items from meeting discussions.
*   **Web-based Interface:** The `app` directory includes a web interface for interacting with the agent.
*   **Command Line Interface:** The `cli` directory offers a command-line interface for demo and testing purposes.

## Prerequisites & Dependencies

Before you begin, ensure you have the following installed:

*   **Python 3.7+**
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

    uv pip install -r requirements.txt # create a requirements.txt if needed
    ```

3.  **Set up the web application:**

    Navigate to the `app/static` directory and install any necessary JavaScript dependencies (if any). Currently it does not seem to require any build steps with npm, but if needed use the commands:

    ```bash
    cd app/static
    # npm install  # If there is a package.json file
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

1.  **Connect:** Click the "Connect" button on the web interface to establish a real-time session with the agent.
2.  **Speak:** The application should automatically start capturing audio. Speak naturally into your microphone.
3.  **Observe:** Monitor the agent's output, which should include extracted action items and other relevant information.

### Command-Line Interface

The `cli` directory contains scripts for demo and testing purposes.

1.  **Run the demo script:**

    ```bash
    cd cli
    python demo.py
    ```

    This will likely run a command-line demonstration of the agent's capabilities.

2.  **Run the UI script:**

    ```bash
    cd cli
    python ui.py
    ```

    This may provide a command line user interface for the tool.

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