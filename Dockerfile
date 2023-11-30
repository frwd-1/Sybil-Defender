# Build stage: compile Python dependencies and obfuscate code
FROM ubuntu:focal as builder

# Install Python and dependencies
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y python3.10 python3.10-dev python3.10-venv python3.10-distutils
RUN apt-get install -y build-essential libffi-dev libssl-dev
RUN python3.10 -m ensurepip
RUN python3.10 -m pip install --upgrade pip
COPY requirements.txt ./
RUN python3.10 -m pip install --user -r requirements.txt --no-cache-dir

# Install pyarmor and obfuscate code
RUN python3.10 -m pip install pyarmor
ENV PATH="/root/.local/bin:${PATH}"
# RUN echo $(python3.10 -m pip show pyarmor | grep Location)
COPY ./src /app/src
RUN pyarmor gen -O /app/src/hydra_obfuscated -r /app/src/hydra

# Final stage: set up environment with Node.js and obfuscated Python code
FROM ubuntu:focal

# Install Python 3.10 and Node.js
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y curl gnupg software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get install -y python3.10
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get -y install nodejs

COPY --from=builder /root/.local /root/.local


# Set environment variables
ENV PATH=/root/.local/bin:$PATH
ENV NODE_ENV=production

# Enable agent logging if needed
LABEL "network.forta.settings.agent-logs.enable"="true"

WORKDIR /app
# Copy the Python runtime dependencies and obfuscated code from the builder stage
COPY --from=builder /app/src/hydra_obfuscated ./src
COPY --from=builder /app/src/hydra_obfuscated/pyarmor_runtime_000000 ./pyarmor_runtime_000000

COPY /src/db ./src/db
COPY /src/g ./src/g
COPY /src/constants.py ./src
COPY /src/agent.py ./src
COPY package*.json ./
COPY LICENSE.md ./

# Install Node dependencies
RUN npm ci --production

# Start command
CMD ["npm", "run", "start:prod"]
