# Smart Intensive Care Unit (SICU)

![version](https://img.shields.io/badge/version-0.1.0-blue)
![python](https://img.shields.io/badge/python-3.9-blue)
![license](https://img.shields.io/badge/license-MIT-green)

<p align="center">
  <img src="https://github.com/Smmehdihosseini/SICU/blob/main/Streamlit/.streamlit/sicu_sidebar.png" alt="Smart Internsive Care Unit">
</p>

<p align="center">
  <a href="https://www.youtube.com/your-channel-or-video-link">
    <img src="https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg" alt="YouTube" width="200"/>
  </a>
</p>


## Table of Contents
- [Description](#description)
- [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
- [Usage](#usage)
- [License](#license)
- [Contact](#contact)

## Description

In the landscape of modern healthcare, the Intensive Care Unit (ICU) is a critical component where timely, accurate, and specialized care is needed around the clock. The IoT-enabled SICU System is a pioneering project that integrates the power of Internet of Things (IoT) with healthcare to ensure optimal patient care.

This system incorporates a network of sensors and medical devices that work seamlessly together. By collecting and processing real-time health data, it supports healthcare professionals in monitoring and decision-making processes. These interconnected devices continuously monitor various patient parameters such as heart rate, blood pressure and oxygen levels, and more. This information is instantly available to the medical staff, ensuring that any health abnormalities can be detected and treated immediately.

One of the standout features of this system is its real-time analytics capability. By analyzing patterns in the data, it can detect signs of health deterioration and alert the medical team.

Furthermore, this system reduces the physical interaction required between healthcare workers and patients, thereby minimizing the risk of cross-contamination, especially important in the times of infectious diseases.

Finally, the system is designed with an easy-to-use interfaces including web application and telegram bot that prioritizes crucial information, ensuring healthcare providers can quickly and accurately evaluate patient status and administer necessary treatments.

By integrating technology and healthcare, the IoT-enabled SICU System enhances the quality of care, improves patient outcomes, and offers a new dimension of support in critical care environments.

## Getting Started

### Prerequisites

This project requires Python 3.8 (or newer). It is recommended to use a virtual environment to avoid conflicts with other projects or system-wide packages. Here are the instructions for setting up a virtual environment using either Anaconda or `venv`:

### Anaconda

If you're using [Anaconda](https://www.anaconda.com/products/distribution), you can create a new environment as follows:

1. Open the Anaconda Prompt.
2. Create a new environment. Replace `sicu` with your desired environment name.
    ```
    conda create -n sicu python=3.8
    ```
3. Activate the environment.
    ```
    conda activate sicu
    ```
4. Install the required packages.
    ```
    pip install -r requirements.txt
    ```

### Python venv

If you prefer to use Python's built-in `venv` module, you can create a new virtual environment as follows:

1. Open the terminal.
2. Navigate to the project directory.
3. Create a new environment. Replace `sicu` with your desired environment name.
    ```
    python3 -m venv sicu
    ```
4. Activate the environment.
    - On Windows:
        ```
        .\sicu\Scripts\activate
        ```
    - On Unix or MacOS:
        ```
        source sicu/bin/activate
        ```
5. Install the required packages.
    ```
    pip install -r requirements.txt
    ```

After setting up the virtual environment and installing the required packages, you can proceed with the [Usage](#usage) instructions. It should be noted that you can consider separate virtual enviornments for each microservice. Consider installing the `requirements.txt` in each subdirecrtories for that specific microservice.
    
## Usage

You can also check out demo walkthrough video on [Youtube](https://www.youtube.com/watch?v=D4x3aPz1dGk)!

1. Change directory to the main directory of repository.
2. Before executing any files remember to check the `conf` and `settings` files in each directory and change them according to your needs in that service. 
3. Stay in this directory and run the microservices using this command in your terminal or command line:
    -
    ```
    python -m <EXAMPLEFOLDER>.<EXAMPLESERVICE>
    ```
4. For example, in order to run the Service Catalog, you should use:
    -
    ```
    python -m Catalog.service_catalog
    ```
5. The only microservice that needs to be executed in the subdirectory is the Streamlit Web Application. In order to do that you have to change directory to Streamlit folder and run:
    ```
    streamlit run app.py
    ```

**Note!** You can run all the services in optional order since the services and devices will wait until they can register themselves to the registery system but it's prefered to run the services and files in this order to make sure that everything works fine:
1. Service Catalog
2. Device Catalog
3. MongoDB
4. Analysis
5. Device Gateway
6. Streamlit Web Application/Telegram Bot

**Note!** The mentioned token in the telegram bot settings file has been revoked, you have to use your own token to access the bot. You can find our telegram bot currently on [Telegram](https://t.me/sicuappbot)

## License

This project has been done for the project of Programming for IoT Application course under supervision of Prof. Edoardo Patti.

Here is the list of people who have contributed to the project to be done:

- Seyed Mohammad Mehdi Hosseini
- Riccardo Smeriglio
- Sonia Ciuffreda
- Elaheh Lotfimahyari

We would be so happy to recieve your opiniion regarding our work, feel free to email us and open issues.

MIT Licence

## Contact

You can find this email address to contact the SICU project members:
mehdi.hosseini@studenti.polito.it

