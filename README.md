# utilities for onboarding models to openad toolkit

⚠️ Under construction

### Model implementations

model implementation for [generation example](examples/generation)

model implementation for [properties example](examples/properties)


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

the bucket should follow the gt4sd path scheme

`algorithm_type / algorithm_name / algorithm_application / algorithm_version`

For testing you can create the path locally to skip downloading from s3. the same scheme applies under the users home directory `.gt4sd` directory:

`.gt4sd / (algorithms, properties) / algorithm_type / algorithm_name / algorithm_application / algorithm_version`