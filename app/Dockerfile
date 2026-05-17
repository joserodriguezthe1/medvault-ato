# =============================================================================
# MedVault API - hardened container image
#
# Controls satisfied by this Dockerfile:
#   CM-7   Least Functionality   (distroless base - no shell, no package manager)
#   AC-6   Least Privilege       (non-root user)
#   SR-3   Supply Chain          (pinned base image)
#   SI-7   Integrity             (multi-stage build; final image has only what is needed)
# =============================================================================

# ---- Stage 1: build dependencies in a full Python image ---------------------
# Must match the distroless Python version (3.11)
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
# Install with --target into a directory we control. PYTHONPATH in the final
# stage will point Python at this location.
RUN pip install --no-cache-dir --target=/packages -r requirements.txt

# ---- Stage 2: distroless runtime --------------------------------------------
FROM gcr.io/distroless/python3-debian12:nonroot

WORKDIR /app

# Copy installed packages and source.
COPY --from=builder /packages /packages
COPY src/ /app/

# Tell Python where to find our packages AND the app source.
ENV PYTHONPATH=/packages:/app

USER 65532:65532

EXPOSE 8000

ENTRYPOINT ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]