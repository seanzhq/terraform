variable "namespace" {
    type        = string
    description = "Prefix of the resource names"
}

variable "environment" {
    type        = string
    description = "Environment suffix for the resource names"
    validation {
        condition     = contains(["dev", "preprod", "prod"], var.environment)
        error_message = "Allowed values for environment are \"dev\", \"preprod\", or \"prod\"."
    }
}
