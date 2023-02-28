# Example generator

A CI job takes care of updating the [examples](../) by building the [example template](example_template.sh) with the different configurations defined in the [use cases](./use_cases/).

In order to favor the `development --> QA --> master` workflow and to avoid duplicate pipelines, this CI job only runs on development branches.

## The template

The [example template](./example_template.sh) contains a `CONFIG_FILE_CREATION` comment that serves as reference. The config for the actual examples will be placed under this comment by the CI job.

## Use cases

Each use case is defined by a `.cfg` file in the [use-case directory](./use_cases/). For each `.cfg` file, an example file will be created by inserting the configuration into the [example template](example_template.sh).

Note that the path of the `.cfg` file relative to the use-case directory is preserved, meaning that the same folder structure will be present in the [examples folder](../).