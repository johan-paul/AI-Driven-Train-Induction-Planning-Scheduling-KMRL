// src/components/TrainGroups.jsx
import React, { useState } from "react";
import TrainCard from "./TrainCard";
import TrainDetailsModal from "./TrainDetailsModal";

export default function TrainGroups({ groups = [] }) {
  const [selectedTrain, setSelectedTrain] = useState(null);

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {groups.map((group) => (
          <div key={group.name} className="space-y-4">
            <h2 className="text-xl font-bold flex items-center">
              <span className="inline-block w-3 h-3 rounded-full mr-2" style={{ background: group.color }} />
              {group.name} — {group.trains?.length ?? 0}
            </h2>

            {group.trains?.map((train) => (
              <TrainCard
                key={train.id ?? train.train_id}
                train={train}
                color={group.color}
                onViewDetails={setSelectedTrain}
              />
            ))}
          </div>
        ))}
      </div>

      {selectedTrain && (
        <TrainDetailsModal train={selectedTrain} onClose={() => setSelectedTrain(null)} />
      )}
    </>
  );
}
