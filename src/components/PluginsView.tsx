import type { PermissionSection } from "../connections/connectionTypes";
import { PermissionSectionList } from "./PermissionSectionList";
import "./PluginsView.css";

interface PluginsViewProps {
  error?: string;
  sections: PermissionSection[];
  onError: (message: string) => void;
  onPermissionChange: (permissionId: string, enabled: boolean) => void;
}

export function PluginsView({ error, sections, onError, onPermissionChange }: PluginsViewProps) {
  return (
    <>
      <h1 className="plugins-view__title">Plugins</h1>
      <section className="plugins-view" aria-label="Sherpa plugins">
        {error ? <p className="plugins-view__error" role="alert">{error}</p> : null}
        <PermissionSectionList
          sections={sections.filter((section) => section.id !== "workspace")}
          onConnectionError={onError}
          onPermissionChange={onPermissionChange}
        />
      </section>
    </>
  );
}
