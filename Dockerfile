# Build stage: compile Python dependencies
FROM python:3.8.10 as builder
RUN python -m pip install --upgrade pip
COPY requirements.txt ./
# Install other packages to user's local directory
RUN python -m pip install --user -r requirements.txt

# Final stage: use ubuntu:focal
FROM ubuntu:focal

# Install system dependencies for your app (e.g., curl, gnupg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (if your app requires it)
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash - \
    && apt-get install -y nodejs

# Copy Python dependencies installed in user's local directory from the builder
COPY --from=builder /root/.local /root/.local

# Ensure the local Python dependencies are in PATH
ENV PATH=/root/.local/bin:$PATH
ENV NODE_ENV=production

# Enable agent logging if necessary
LABEL "network.forta.settings.agent-logs.enable"="true"

# Set the working directory
WORKDIR /app

# Copy the application's source code into the container
COPY ./src ./src

# Copy Node.js package manifest files
COPY package*.json ./

# Install Node.js dependencies for the application
RUN npm ci --production

# Command to run the application
CMD [ "npm", "run", "start:prod" ]
