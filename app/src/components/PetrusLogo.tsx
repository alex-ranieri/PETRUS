import { useTranslation } from "react-i18next";
import logo from "../assets/petrus-logo.png";

export default function PetrusLogo({
  variant = "medium",
  className = "",
}: {
  variant?: "small" | "medium" | "large" | "hero";
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <img
      className={`petrus-logo logo-${variant} ${className}`}
      src={logo}
      alt={t("brand.logoAlt")}
      width={1536}
      height={1536}
    />
  );
}
