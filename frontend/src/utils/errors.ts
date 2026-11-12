export class ApiError extends Error {
  error_code: string

  constructor(error_code: string, message: string) {
    super(message)
    this.error_code = error_code
  }
}
