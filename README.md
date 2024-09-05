# utilities for onboarding models to openad toolkit

⚠️ Under construction

## Model Implementations

Look under the examples folder for implementations of models.

- implementation for generation models [readme](examples/generation)
- implementation for properties example [readme](examples/properties)


## Use your own private model not hosted on gt4sd
set the following variables in the os host or python script to your private s3 buckets:

```python
import os
os.environ["GT4SD_S3_HOST"] = "s3.<region>.amazonaws.com"
os.environ["GT4SD_S3_ACCESS_KEY"] = ""
os.environ["GT4SD_S3_SECRET_KEY"] = ""
os.environ["GT4SD_S3_HOST_HUB"] = "s3.<region>.amazonaws.com"
os.environ["GT4SD_S3_ACCESS_KEY_HUB"] = ""
os.environ["GT4SD_S3_SECRET_KEY_HUB"] = ""
```

## Local Cache locations for models

### Generation Models location

`~/.gt4sd / algorithms / algorithm_type / algorithm_name / algorithm_application / algorithm_version`

### Property Models location

`~/.gt4sd / properties / domain / algorithm_name / algorithm_application / algorithm_version`
