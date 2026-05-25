/**
 * PermissionGate — conditionally renders children based on user permissions.
 *
 * Usage:
 *   <PermissionGate perm="finance.payment.record">
 *     <Button>Record Payment</Button>
 *   </PermissionGate>
 *
 *   <PermissionGate perm="grades.approve" fallback={<span>View only</span>}>
 *     <ApproveButton />
 *   </PermissionGate>
 */

import { useAuthStore } from "@/stores/authStore";

interface Props {
  perm:     string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export default function PermissionGate({ perm, children, fallback = null }: Props) {
  const { can } = useAuthStore();
  return can(perm) ? <>{children}</> : <>{fallback}</>;
}
