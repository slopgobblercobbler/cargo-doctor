/**
 * Cargo.toml Sample Presets for Cargo Doctor
 */

export const PRESET_STANDARD_BINARY = `[package]
name = "ripgrep-lite"
version = "0.4.2"
edition = "2021"
rust-version = "1.75.0"
description = "Ultra-fast recursive search utility built in pure Rust"
license = "MIT OR Apache-2.0"
repository = "https://github.com/slopgobblercobbler/ripgrep-lite"
readme = "README.md"

[dependencies]
clap = { version = "4.5.4", features = ["derive", "env"] }
regex = "1.10.4"
walkdir = "2.5.0"
memmap2 = "0.9.4"
crossbeam-channel = "0.5.12"
serde = { version = "1.0.201", features = ["derive"] }
serde_json = "1.0.117"

[dev-dependencies]
tempfile = "3.10.1"
criterion = "0.5.1"

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
strip = true
panic = "abort"
`;

export const PRESET_WORKSPACE = `[workspace]
members = [
  "crates/core",
  "crates/cli",
  "crates/server"
]
resolver = "2"

[workspace.package]
version = "1.2.0"
edition = "2021"
rust-version = "1.76.0"
license = "MIT"
repository = "https://github.com/slopgobblercobbler/mesh-engine"
authors = ["slopgobblercobbler <slopgobblercobbler@users.noreply.github.com>"]

[workspace.dependencies]
tokio = { version = "1.38.0", features = ["full"] }
serde = { version = "1.0.203", features = ["derive"] }
tracing = "0.1.40"
tracing-subscriber = "0.3.18"
anyhow = "1.0.86"
thiserror = "1.0.61"

[profile.release]
opt-level = 3
lto = "thin"
codegen-units = 1
strip = true
`;

export const PRESET_VULNERABLE = `[package]
name = "legacy-crypto-miner"
version = "0.1.0"
# Notice: Missing description, missing license, missing readme, missing rust-version
edition = "2015"

[dependencies]
# Error: Wildcard version dependency
rand = "*"

# Warning: Unpinned git dependency tracking main branch without rev or tag
hyper = { git = "https://github.com/hyperium/hyper", branch = "master" }

# Warning: Open-ended inequality bound
tokio = ">= 1.0"

# Warning: Duplicate dependency with mismatched version compared to dev-dependencies
serde = "1.0.180"

[dev-dependencies]
serde = "1.0.200"
test-log = "*"
`;

export const PRESET_OPTIMIZED_RELEASE = `[package]
name = "ultra-engine"
version = "2.0.0"
edition = "2021"
rust-version = "1.78.0"
description = "Mission-critical high-throughput asynchronous stream processing engine"
license = "Apache-2.0"
repository = "https://github.com/slopgobblercobbler/ultra-engine"
readme = "README.md"

[dependencies]
tokio = { version = "1.38.0", features = ["macros", "rt-multi-thread"] }
axum = "0.7.5"
tower = "0.4.13"
serde = { version = "1.0.203", features = ["derive"] }
simd-json = "0.13.10"
parking_lot = "0.12.3"
dashmap = "5.5.3"

[profile.release]
opt-level = 3
lto = "fat"
codegen-units = 1
strip = "symbols"
panic = "abort"
overflow-checks = false
`;
