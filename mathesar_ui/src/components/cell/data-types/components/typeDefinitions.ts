import type { SelectProps } from '@mathesar-component-library/types';

export interface CellTypeProps<Value> {
  value: Value | null | undefined;
  isActive: boolean;
  disabled: boolean;
}

// TextBox

export interface TextBoxCellExternalProps {
  length?: number | null;
}

export interface TextBoxCellProps
  extends CellTypeProps<string>,
    TextBoxCellExternalProps {}

// TextArea

export type TextAreaCellExternalProps = TextBoxCellExternalProps;

export type TextAreaCellProps = TextBoxCellProps;

// Number

export interface NumberCellExternalProps {
  locale?: string;
  allowFloat: boolean;
  isPercentage: boolean;
}

export interface NumberCellProps
  extends CellTypeProps<string | number>,
    NumberCellExternalProps {}

// Money

export interface MoneyCellExternalProps {
  currencySymbol: string;
  currencySymbolLocation: 'after-minus' | 'end-with-space';
  locale?: string;
  allowFloat: boolean;
}

export interface MoneyCellProps
  extends CellTypeProps<string | number>,
    MoneyCellExternalProps {}

// Checkbox

export type CheckBoxCellExternalProps = Record<string, never>;

export type CheckBoxCellProps = CellTypeProps<boolean>;

// SingleSelect

export type SingleSelectCellExternalProps<Option> = Pick<
  SelectProps<Option>,
  'options' | 'getLabel'
>;

export interface SingleSelectCellProps<Option>
  extends CellTypeProps<Option>,
    SingleSelectCellExternalProps<Option> {}

export type HorizontalAlignment = 'left' | 'right' | 'center';
