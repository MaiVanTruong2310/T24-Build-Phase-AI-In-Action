import * as E from 'fp-ts/Either';
import { pipe } from 'fp-ts/function';
import { DoctorForm, FieldErrors } from './FormTypes';

const validateRequired = (value: string, errorMsg: string): E.Either<string, string> =>
  value.trim().length > 0 ? E.right(value.trim()) : E.left(errorMsg);

const validateEmail = (email: string): E.Either<string, string> =>
  email.includes('@') && email.includes('.') ? E.right(email.trim()) : E.left('Email không hợp lệ');

export const validateDoctorForm = (form: DoctorForm): E.Either<FieldErrors, DoctorForm> => {
  const errors: FieldErrors = {};

  pipe(validateRequired(form.fullName, 'Họ và tên là bắt buộc'), E.mapLeft(e => { errors.fullName = e }));
  pipe(validateRequired(form.academicTitle, 'Học hàm/Học vị là bắt buộc'), E.mapLeft(e => { errors.academicTitle = e }));
  
  if (form.email) {
     pipe(validateEmail(form.email), E.mapLeft(e => { errors.email = e }));
  }

  pipe(validateRequired(form.licenseNumber, 'Số CCHN là bắt buộc'), E.mapLeft(e => { errors.licenseNumber = e }));
  
  return Object.keys(errors).length > 0
    ? E.left(errors)
    : E.right(form);
};
