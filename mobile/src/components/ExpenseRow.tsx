import { Text, View } from "react-native";

import type { Expense, Member } from "@/api/types";
import { categoryInfo, expenseEmoji } from "@/constants/categories";
import { relativeDay } from "@/lib/dates";
import { formatCents } from "@/lib/money";
import { colorFor, firstName } from "@/lib/people";
import { Avatar, Muted, Press, T } from "./ui";

export function ExpenseRow({
  expense, members, showDate = true, onPress,
}: {
  expense: Expense;
  members: Member[];
  showDate?: boolean;
  onPress?: () => void;
}) {
  const cat = categoryInfo(expense.category);
  const meta = [firstName(expense.author.display_name), cat.label, showDate ? relativeDay(expense.spent_at) : null]
    .filter(Boolean)
    .join(" · ");
  return (
    <Press onPress={onPress} disabled={!onPress} haptic={false} accessibilityLabel={`${expense.description}, ${formatCents(expense.amount_cents)}`}>
      <View className="flex-row items-center gap-3 py-3">
        <View className="h-11 w-11 items-center justify-center rounded-2xl bg-accent-soft dark:bg-accent-softDark">
          <Text style={{ fontSize: 20 }}>{expenseEmoji(expense.category, expense.icon_key)}</Text>
        </View>
        <View className="flex-1">
          <T className="font-semibold text-[15px]" numberOfLines={1}>
            {expense.description}
          </T>
          <View className="mt-1 flex-row items-center gap-1.5">
            <Avatar name={expense.author.display_name} color={colorFor(expense.author.id, members)} size={18} ring={false} />
            <Muted className="flex-1 text-xs" numberOfLines={1}>
              {meta}
            </Muted>
          </View>
        </View>
        <T className="font-semibold text-[15px]">{formatCents(expense.amount_cents)}</T>
      </View>
    </Press>
  );
}
