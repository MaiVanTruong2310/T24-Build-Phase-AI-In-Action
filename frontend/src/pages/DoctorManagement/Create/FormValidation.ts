import * as E from 'fp-ts/Either';
import { pipe } from 'fp-ts/function';
import { DoctorForm, FieldErrors } from './FormTypes';
import { birthDateError, citizenIdError, emailError } from '../../../features/appointment-booking/dateValidation';

const validateRequired = (value: string, errorMsg: string): E.Either<string, string> =>
  value.trim().length > 0 ? E.right(value.trim()) : E.left(errorMsg);

export const validateDoctorForm = (form: DoctorForm): E.Either<FieldErrors, DoctorForm> => {
  const errors: FieldErrors = {};

  pipe(validateRequired(form.fullName, 'Họ và tên là bắt buộc'), E.mapLeft(e => { errors.fullName = e }));
  pipe(validateRequired(form.academicTitle, 'Học hàm/Học vị là bắt buộc'), E.mapLeft(e => { errors.academicTitle = e }));
  
  if (form.email) {
    const err = emailError(form.email);
    if (err) errors.email = err;
  }

  if (form.dateOfBirth) {
    const err = birthDateError(form.dateOfBirth);
    if (err) errors.dateOfBirth = err;
  }

  if (form.idNumber) {
    const err = citizenIdError(form.idNumber);
    if (err) errors.idNumber = err;
  }

  pipe(validateRequired(form.licenseNumber, 'Số CCHN là bắt buộc'), E.mapLeft(e => { errors.licenseNumber = e }));
  
  return Object.keys(errors).length > 0
    ? E.left(errors)
    : E.right(form);
};
