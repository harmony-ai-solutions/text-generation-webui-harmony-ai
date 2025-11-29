# Dockerfile for Text-Generation-WebUI AMD WSL2
# Uses PyTorch base image from Harmony AI quickstart repo
FROM harmonyai/base-pytorch-rocm-wsl2:2.7.1-latest
ARG APP_UID="${APP_UID:-6972}"
ARG APP_GID="${APP_GID:-6972}"

# Set home dir
ENV HOME=/app/text-generation-webui
WORKDIR $HOME

# Allow statements and log messages to immediately appear
ENV PYTHONUNBUFFERED=True

# Install system dependencies
RUN apt-get update && \
    apt-get install -y git && \
    rm -rf /var/lib/apt/lists/*

# Clone repository
RUN git clone https://github.com/harmony-ai-solutions/text-generation-webui-harmony-ai.git $HOME

# Install requirements excluding torch/torchaudio (already in base image)
# Also handle any AVX2 variants
RUN pip install --force-reinstall --no-deps --ignore-installed --break-system-packages blinker # This breaks pip install despite using --break-system-packages; so manually handle this beforehand
RUN grep -v '^torch' requirements/full/requirements_amd.txt | grep -v '^torchaudio' > requirements_notorch.txt && \
    pip install --no-cache-dir --break-system-packages -r requirements_notorch.txt

# Copy entrypoint
COPY entrypoint.sh docker/amd-wsl/entrypoint.sh
RUN chmod +x docker/amd-wsl/entrypoint.sh

# Create user_data directory
RUN mkdir -p user_data

# Export WSL2-specific ROCm environment variables
ENV LLVM_SYMBOLIZER_PATH=/opt/rocm/llvm/bin/llvm-symbolizer
ENV PATH=$PATH:/opt/rocm/bin
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/rocm/lib
ENV HIP_VISIBLE_DEVICES=0
ENV ROCM_PATH=/opt/rocm

# Set proper permissions
RUN chown -R 1000:1000 ${HOME}
USER 1000:0

EXPOSE 7860 5000

ENTRYPOINT ["/app/text-generation-webui/docker/amd-wsl/entrypoint.sh"]
